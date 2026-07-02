"""
FINAL FORMULA VERIFICATION:
  Outstanding = Op_Bal + SI_NetTotal - TRAN_DETAIL_Cr - TRAN_MASTER_Cr - AUTOJOURNAL_Cr

Expected results:
    20133 ~ 48,062,253 (within a few thousand due to timing)
    25469 =    435,606
    18518 =  5,782,164
"""
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

SQL_SERVER = os.getenv("SQL_SERVER", "INDIASERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE", "Acc2026_2027")
SQL_USER = os.getenv("SQL_USER", "balar_sync")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "")

TARGETS = {20133: 48062253.0, 25469: 435606.0, 18518: 5782164.0}


def conn():
    cs = (
        f"DRIVER={{SQL Server}};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};"
        f"UID={SQL_USER};PWD={SQL_PASSWORD};ApplicationIntent=ReadOnly;"
    )
    c = pyodbc.connect(cs, readonly=True)
    c.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
    return c


def main():
    c = conn()
    cur = c.cursor()

    print("=== FINAL FORMULA: Op + SI_Net - TranDetail_Cr - TranMaster_Cr - AutoJournal_Cr ===\n")

    for pid, target in TARGETS.items():
        cur.execute(f"""
            SELECT
                (SELECT ISNULL(Lgr_Op_Bal,0) FROM LEDGER_DETAIL
                 WHERE Lgr_Id={pid} AND Cmp_Code=1) AS op_bal,

                (SELECT ISNULL(SUM(ISNULL(Sal_Inv_NetTotal,0)),0) FROM SALES_INVOICE
                 WHERE Lgr_Id={pid} AND Cmp_Code=1) AS si_net,

                (SELECT ISNULL(SUM(ISNULL(Tran_Amount,0)),0) FROM TRAN_DETAIL
                 WHERE Tran_Detail_Id={pid} AND Tran_DrCr='C' AND Cmp_Code=1) AS td_cr,

                (SELECT ISNULL(SUM(ISNULL(Tran_Amount,0)),0) FROM TRAN_MASTER
                 WHERE Tran_Master_Id={pid} AND Tran_DrCr='C' AND Cmp_Code=1) AS tm_cr,

                (SELECT ISNULL(SUM(ISNULL(CrAmount,0)),0) FROM AUTOJOURNAL
                 WHERE Lgr_Id={pid} AND Cmp_Code=1) AS aj_cr
        """)
        row = cur.fetchone()
        op, si, td, tm, aj = [float(x) if x else 0.0 for x in row]
        outstanding = op + si - td - tm - aj
        delta = outstanding - target
        status = "EXACT" if abs(delta) < 100 else f"off by {delta:,.0f}"

        print(f"  Party {pid}: Op={op:,.0f} + SI={si:,.0f} - TD_Cr={td:,.0f} - TM_Cr={tm:,.0f} - AJ_Cr={aj:,.0f}")
        print(f"    = {outstanding:,.0f}   (target={target:,.0f})  [{status}]")
        print()

    c.close()
    print("DONE")


if __name__ == "__main__":
    main()
