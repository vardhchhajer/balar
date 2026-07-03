"""
PROC_OUTSTANDING exact replication v3.

CRITICAL FIX: Bills come from CURRENT-YEAR PARTYDETAIL only.
Previous-year data contributes ONLY on-account receipts (SQLONACCOUNT3/4/7).

Formula:
  outstanding = SUM(PD.BILL_AMOUNT - AM.ADJUSTAMT - AM.TOTAL - AM.INTEREST + AM.INTREC)
                  FROM curr PARTYDETAIL (all JOBFLAG)
              - onacc_curr_d   [curr TRAN_DETAIL.PARTAMOUNT, types BR/CR/YSR/BP/CP/DN/CN/J]
              - onacc_curr_m6  [curr SR/GCN/GDN: TM.TRAN_AMOUNT where TD.PARTAMOUNT>0, SHOWPARTAMT=1/NULL]
              - adv_curr        [curr ADVANCE_ENTRY.PARTAMOUNT]
              - onacc_prev_d   [prev TRAN_DETAIL.PARTAMOUNT, same filter as curr]
              - onacc_prev_m7  [prev SR/GCN/GDN: TM.TRAN_AMOUNT where TD.PARTAMOUNT>0, TM.SHOWPARTAMT=1/NULL]
              - adv_prev        [prev ADVANCE_ENTRY.PARTAMOUNT]

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
    """Bills from PARTYDETAIL (all JOBFLAG) minus ADJMASTER receipts.
    Aggregates ADJMASTER per bill first to avoid row multiplication.
    Floors each bill's net at 0 (can't have negative outstanding per bill)."""
    return one(cur, f"""
        SELECT SUM(CASE WHEN net > 0 THEN net ELSE 0 END) FROM (
            SELECT
                ISNULL(PD.BILL_AMOUNT, 0)
                - ISNULL(am.adj, 0)
                - ISNULL(am.tot, 0)
                - ISNULL(am.interest, 0)
                + ISNULL(am.intrec, 0) AS net
            FROM PARTYDETAIL PD
            LEFT JOIN (
                SELECT BILLNO, FLAG, VCODE, CMP_CODE,
                       SUM(ISNULL(ADJUSTAMT,0))  AS adj,
                       SUM(ISNULL(TOTAL,0))      AS tot,
                       SUM(ISNULL(INTEREST,0))   AS interest,
                       SUM(ISNULL(INTREC,0))     AS intrec
                FROM ADJMASTER
                WHERE LGR_ID={pid} AND CMP_CODE=1 AND RECDATE<='{ason}'
                GROUP BY BILLNO, FLAG, VCODE, CMP_CODE
            ) am ON am.BILLNO=PD.BILL_NO AND am.FLAG=PD.JOBFLAG
                  AND am.CMP_CODE=PD.CMP_CODE AND am.VCODE=PD.VCODE
            WHERE PD.LGR_ID={pid} AND PD.CMP_CODE=1 AND PD.DATE<='{ason}'
        ) t
    """)


def get_onacc_d(cur, pid, ason):
    """TRAN_DETAIL.PARTAMOUNT credits - unallocated on-account."""
    return one(cur, f"""
        SELECT ISNULL(SUM(ISNULL(TD.PARTAMOUNT,0)),0)
        FROM TRAN_DETAIL TD
        INNER JOIN TRAN_MASTER TM ON TM.TRAN_ID=TD.TRAN_ID
            AND TM.TRAN_TYPE=TD.TRAN_TYPE AND TD.CMP_CODE=TM.CMP_CODE
        WHERE TD.Tran_Detail_Id={pid} AND TD.CMP_CODE=1 AND TD.TRAN_DRCR='C'
          AND ISNULL(TD.PARTAMOUNT,0)>0
          AND (TD.SHOWPARTAMT=1 OR TD.SHOWPARTAMT IS NULL)
          AND (TD.REC_TRANS=0 OR TD.REC_TRANS IS NULL)
          AND TD.TRAN_TYPE IN ('BR','CR','YSR','BP','CP','DN','CN','J')
          AND TM.TRAN_DATE<='{ason}'
    """)


def get_onacc_m(cur, pid, ason):
    """SQLONACCOUNT6/7: SR/GCN/GDN via TM.TRAN_AMOUNT where TD.PARTAMOUNT>0 and TM.SHOWPARTAMT=1/NULL."""
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
          AND TM.TRAN_DRCR='C'
          AND TM.TRAN_DATE<='{ason}'
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

        # Current year: bills (from PARTYDETAIL) + all on-account
        bills   = get_bills_adj(cur_c, pid, ASON)
        onacc_d = get_onacc_d(cur_c, pid, ASON)
        onacc_m = get_onacc_m(cur_c, pid, ASON)
        adv     = get_adv(cur_c, pid, ASON)

        # Previous year: on-account ONLY (receipts), NO bills
        onacc_dp = get_onacc_d(cur_p, pid, ASON)
        onacc_mp = get_onacc_m(cur_p, pid, ASON)
        adv_p    = get_adv(cur_p, pid, ASON)

        # Debug: show raw prev-year TRAN_DETAIL PARTAMOUNT (no date filter via TM)
        raw_prev_partamt = one(cur_p, f"""
            SELECT ISNULL(SUM(ISNULL(TD.PARTAMOUNT,0)),0) FROM TRAN_DETAIL TD
            WHERE TD.Tran_Detail_Id={pid} AND TD.CMP_CODE=1 AND TD.TRAN_DRCR='C'
              AND ISNULL(TD.PARTAMOUNT,0)>0
              AND (TD.SHOWPARTAMT=1 OR TD.SHOWPARTAMT IS NULL)
              AND (TD.REC_TRANS=0 OR TD.REC_TRANS IS NULL)
              AND TD.TRAN_TYPE IN ('BR','CR','YSR','BP','CP','DN','CN','J')
        """)

        vals = [bills, onacc_d, onacc_m, adv, onacc_dp, onacc_mp, adv_p]
        if all(isinstance(x, float) for x in vals):
            out = bills - onacc_d - onacc_m - adv - onacc_dp - onacc_mp - adv_p
            d = out - target
            ok = abs(d) < 5000
            allok = allok and ok
            print(f"Party {pid}: bills={bills:,.0f} onaccD={onacc_d:,.0f} onaccM={onacc_m:,.0f} "
                  f"prevD={onacc_dp:,.0f} prevM={onacc_mp:,.0f}  raw_prev_partamt={raw_prev_partamt:,.0f}")
            print(f"   OUT={out:,.0f} target={target:,.0f} delta={d:,.0f} {'MATCH' if ok else '***OFF***'}")
        else:
            allok = False
            errs = [(k,v) for k,v in zip('bills od om adv odp omp advp'.split(), vals) if isinstance(v,str)]
            print(f"Party {pid}: ERR {errs}")
        print()

    cc.close()
    cp.close()
    print("ALL MATCH!" if allok else "some off")


if __name__ == "__main__":
    main()
