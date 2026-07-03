"""
PROC_OUTSTANDING exact replication v2.

Key fixes from reading the actual procedure:
1. PARTYDETAIL: include ALL JOBFLAG rows (not just 'S') - proc does LEFT JOIN ADJMASTER
2. SQLONACCOUNT7 (prev-year GCN/SR): filter TM.SHOWPARTAMT=1 OR IS NULL, uses TM.TRAN_AMOUNT
3. SQLONACCOUNT4 (prev-year on-account): uses TD.PARTAMOUNT > 0 from TRAN_DETAIL

Formula per party:
  outstanding = SUM(PD.BILL_AMOUNT - AM.ADJUSTAMT - AM.TOTAL - AM.INTEREST + AM.INTREC)  [all JOBFLAG]
              - onacc_curr_detail   [TRAN_DETAIL.PARTAMOUNT, curr DB, SHOWPARTAMT=1/NULL, types BR/CR/YSR/BP/CP/DN/CN/J]
              - onacc_curr_m6      [TRAN_MASTER SR/GCN/GDN, curr DB, TD.PARTAMOUNT>0, SHOWPARTAMT=1/NULL, uses TM.TRAN_AMOUNT]
              - onacc_prev_detail  [TRAN_DETAIL.PARTAMOUNT, prev DB, same filter]
              - onacc_prev_m7      [TRAN_MASTER SR/GCN/GDN, prev DB, TD.PARTAMOUNT>0, TM.SHOWPARTAMT=1/NULL, TM.TRAN_AMOUNT]
              - adv_curr - adv_prev

Known targets:
    5141=244,288,233  20133=48,062,253  7370=24,079,884
    2879=7,674,924    18518=5,782,164   25469=435,606
"""
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

SQL_SERVER   = os.getenv("SQL_SERVER",   "INDIASERVER")
SQL_USER     = os.getenv("SQL_USER",     "balar_sync")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "")

CURR_DB = "Acc2026_2027"
PREV_DB = "Acc2025_2026"
ASON    = "2026-07-03"
TARGETS = {
    5141: 244288233.0, 20133: 48062253.0, 7370: 24079884.0,
    2879: 7674924.0, 18518: 5782164.0, 25469: 435606.0,
}


def conn(db):
    cs = (f"DRIVER={{SQL Server}};SERVER={SQL_SERVER};DATABASE={db};"
          f"UID={SQL_USER};PWD={SQL_PASSWORD};ApplicationIntent=ReadOnly;")
    c = pyodbc.connect(cs, readonly=True)
    c.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
    return c


def one(cur, sql):
    try:
        cur.execute(sql)
        r = cur.fetchone()
        return float(r[0]) if r and r[0] is not None else 0.0
    except Exception as e:
        return f"ERR:{str(e)[:70]}"


def get_bills_adj(cur, pid, ason):
    """Bills from PARTYDETAIL (ALL JOBFLAG) minus ADJMASTER receipts."""
    return one(cur, f"""
        SELECT SUM(ISNULL(PD.BILL_AMOUNT,0) - ISNULL(AM.ADJUSTAMT,0)
                   - ISNULL(AM.TOTAL,0) - ISNULL(AM.INTEREST,0) + ISNULL(AM.INTREC,0))
        FROM PARTYDETAIL PD
        LEFT JOIN ADJMASTER AM ON AM.BILLNO=PD.BILL_NO AND AM.FLAG=PD.JOBFLAG
            AND AM.CMP_CODE=PD.CMP_CODE AND PD.VCODE=AM.VCODE
            AND AM.RECDATE<='{ason}'
        WHERE PD.LGR_ID={pid} AND PD.CMP_CODE=1 AND PD.DATE<='{ason}'
    """)


def get_onacc_d(cur, pid, ason):
    """TRAN_DETAIL.PARTAMOUNT credits (unallocated on-account)."""
    return one(cur, f"""
        SELECT ISNULL(SUM(ISNULL(TD.PARTAMOUNT,0)),0)
        FROM TRAN_DETAIL TD
        WHERE TD.Tran_Detail_Id={pid} AND TD.CMP_CODE=1 AND TD.TRAN_DRCR='C'
          AND ISNULL(TD.PARTAMOUNT,0)>0
          AND (TD.SHOWPARTAMT=1 OR TD.SHOWPARTAMT IS NULL)
          AND (TD.REC_TRANS=0 OR TD.REC_TRANS IS NULL)
          AND TD.TRAN_TYPE IN ('BR','CR','YSR','BP','CP','DN','CN','J')
    """)


def get_onacc_m6(cur, pid, ason):
    """SQLONACCOUNT6: curr SR/GCN/GDN via TM.TRAN_AMOUNT where TD.PARTAMOUNT>0."""
    return one(cur, f"""
        SELECT ISNULL(SUM(
            CASE WHEN TD.TRAN_TYPE='J' THEN
                CASE WHEN TD.TRAN_DRCR='C' THEN TD.PARTAMOUNT ELSE 0 END
            ELSE TM.TRAN_AMOUNT END),0)
        FROM TRAN_DETAIL TD
        INNER JOIN TRAN_MASTER TM ON TM.TRAN_ID=TD.TRAN_ID
            AND TM.TRAN_TYPE=TD.TRAN_TYPE AND TD.CMP_CODE=TM.CMP_CODE
        WHERE TM.Tran_Master_Id={pid} AND TD.CMP_CODE=1
          AND TD.PARTAMOUNT>0
          AND (TM.SHOWPARTAMT=1 OR TM.SHOWPARTAMT IS NULL)
          AND TM.TRAN_TYPE IN ('SR','GCN','GDN')
          AND (TM.REC_TRANS=0 OR TM.REC_TRANS IS NULL)
          AND TM.TRAN_DRCR='C' AND TM.TRAN_DATE<='{ason}'
    """)


def get_adv(cur, pid, ason):
    return one(cur, f"SELECT ISNULL(SUM(ISNULL(PARTAMOUNT,0)),0) FROM ADVANCE_ENTRY WHERE LGR_ID={pid} AND CMP_CODE=1 AND VDATE<='{ason}'")


def main():
    cc = conn(CURR_DB)
    cp = conn(PREV_DB)
    allok = True

    for pid, target in TARGETS.items():
        cur_c = cc.cursor()
        cur_p = cp.cursor()

        bills_c = get_bills_adj(cur_c, pid, ASON)
        onacc_dc = get_onacc_d(cur_c, pid, ASON)
        onacc_m6 = get_onacc_m6(cur_c, pid, ASON)
        adv_c = get_adv(cur_c, pid, ASON)

        bills_p = get_bills_adj(cur_p, pid, ASON)
        onacc_dp = get_onacc_d(cur_p, pid, ASON)
        onacc_m7 = get_onacc_m6(cur_p, pid, ASON)  # same logic, prev DB
        adv_p = get_adv(cur_p, pid, ASON)

        vals = [bills_c, onacc_dc, onacc_m6, adv_c, bills_p, onacc_dp, onacc_m7, adv_p]
        if all(isinstance(x, float) for x in vals):
            out = (bills_c + bills_p) - (onacc_dc + onacc_dp) - (onacc_m6 + onacc_m7) - (adv_c + adv_p)
            d = out - target
            ok = abs(d) < 5000
            allok = allok and ok
            print(f"Party {pid}:")
            print(f"  curr: bills={bills_c:,.0f} onaccD={onacc_dc:,.0f} onaccM={onacc_m6:,.0f} adv={adv_c:,.0f}")
            print(f"  prev: bills={bills_p:,.0f} onaccD={onacc_dp:,.0f} onaccM={onacc_m7:,.0f} adv={adv_p:,.0f}")
            print(f"  OUT={out:,.0f} target={target:,.0f} delta={d:,.0f} {'MATCH' if ok else '***OFF***'}")
        else:
            allok = False
            print(f"Party {pid}: ERR {[x for x in zip(['bc','od_c','om6','ac','bp','od_p','om7','ap'], vals) if isinstance(x[1],str)]}")
        print()

    cc.close()
    cp.close()
    print("ALL MATCH!" if allok else "some off")


if __name__ == "__main__":
    main()
