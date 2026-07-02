"""
Refined PROC_OUTSTANDING replication. Adds the master-side SR/GCN/GDN credits
(the SQLONACCOUNT6 union) that were missing, and drops SR from the detail-side
on-account list (SR is handled on the master side, per the proc).

outstanding = PARTYDETAIL.BILL_AMOUNT
            - ADJMASTER.(ADJUSTAMT + TOTAL + INTEREST - INTREC)
            - onacc_detail  [TRAN_DETAIL.PARTAMOUNT credits: BR,CR,YSR,BP,CP,DN,CN,J]
            - onacc_master  [TRAN_MASTER.TRAN_AMOUNT credits: SR,GCN,GDN]
            - ADVANCE_ENTRY.PARTAMOUNT

Targets:
    5141=244,288,233  20133=48,062,253  7370=24,079,884
    2879=7,674,924    18518=5,782,164   25469=435,606
"""
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

SQL_SERVER = os.getenv("SQL_SERVER", "INDIASERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE", "Acc2026_2027")
SQL_USER = os.getenv("SQL_USER", "balar_sync")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "")

ASON = "2026-07-31"
TARGETS = {
    5141: 244288233.0, 20133: 48062253.0, 7370: 24079884.0,
    2879: 7674924.0, 18518: 5782164.0, 25469: 435606.0,
}


def conn():
    cs = (f"DRIVER={{SQL Server}};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};"
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


def main():
    c = conn()
    cur = c.cursor()
    allmatch = True
    for pid, target in TARGETS.items():
        bills = one(cur, f"SELECT SUM(ISNULL(BILL_AMOUNT,0)) FROM PARTYDETAIL WHERE LGR_ID={pid} AND CMP_CODE=1 AND DATE<='{ASON}'")
        adj = one(cur, f"SELECT SUM(ISNULL(ADJUSTAMT,0)+ISNULL(TOTAL,0)+ISNULL(INTEREST,0)-ISNULL(INTREC,0)) FROM ADJMASTER WHERE Lgr_Id={pid} AND CMP_CODE=1 AND RECDATE<='{ASON}'")
        onacc_d = one(cur, f"""SELECT SUM(ISNULL(PARTAMOUNT,0)) FROM TRAN_DETAIL
                               WHERE Tran_Detail_Id={pid} AND CMP_CODE=1 AND TRAN_DRCR='C'
                                 AND ISNULL(PARTAMOUNT,0)>0
                                 AND (SHOWPARTAMT=1 OR SHOWPARTAMT IS NULL)
                                 AND (REC_TRANS=0 OR REC_TRANS IS NULL)
                                 AND TRAN_TYPE IN ('BR','CR','YSR','BP','CP','DN','CN','J')""")
        onacc_m = one(cur, f"""SELECT SUM(ISNULL(TRAN_AMOUNT,0)) FROM TRAN_MASTER
                               WHERE Tran_Master_Id={pid} AND CMP_CODE=1 AND TRAN_DRCR='C'
                                 AND TRAN_TYPE IN ('SR','GCN','GDN')
                                 AND TRAN_DATE<='{ASON}'""")
        adv = one(cur, f"SELECT SUM(ISNULL(PARTAMOUNT,0)) FROM ADVANCE_ENTRY WHERE LGR_ID={pid} AND CMP_CODE=1 AND VDATE<='{ASON}'")

        if all(isinstance(x, float) for x in [bills, adj, onacc_d, onacc_m, adv]):
            out = bills - adj - onacc_d - onacc_m - adv
            d = out - target
            ok = abs(d) < 5000
            allmatch = allmatch and ok
            print(f"Party {pid}: bills={bills:,.0f} adj={adj:,.0f} onaccD={onacc_d:,.0f} onaccM={onacc_m:,.0f} adv={adv:,.0f}")
            print(f"   OUT={out:,.0f}  target={target:,.0f}  delta={d:,.0f}  {'MATCH' if ok else '***OFF***'}")
        else:
            allmatch = False
            print(f"Party {pid}: ERR  bills={bills} adj={adj} onaccD={onacc_d} onaccM={onacc_m} adv={adv}")
        print()

    c.close()
    print("ALL MATCH!" if allmatch else "some still off")


if __name__ == "__main__":
    main()
