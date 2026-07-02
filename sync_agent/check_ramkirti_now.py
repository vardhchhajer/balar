"""
Is the RAM KIRTI ~3,323 difference just live-data timing?

Computes our formula value RIGHT NOW and lists the most recent transactions.
Compare the "OUR VALUE NOW" against what the ERP outstanding report shows for
RAM KIRTI at the SAME moment. If they match now (or differ by a recent txn),
it's timing, not a formula error.

Run on INDIASERVER:
    cd C:\\Users\\Administrator\\Downloads\\sync_agent\\sync_agent
    py check_ramkirti_now.py
"""
import os
import pyodbc
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

SQL_SERVER = os.getenv("SQL_SERVER", "INDIASERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE", "Acc2026_2027")
SQL_USER = os.getenv("SQL_USER", "balar_sync")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "")

PID = 20133
EARLIER_ERP_READING = 48062253.0


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

    print(f"Query time: {datetime.now()}\n")

    op = cur.execute(f"SELECT ISNULL(Lgr_Op_Bal,0) FROM LEDGER_DETAIL WHERE Lgr_Id={PID} AND Cmp_Code=1").fetchone()[0]
    op = float(op or 0)
    si = float(cur.execute(f"SELECT ISNULL(SUM(ISNULL(Sal_Inv_NetTotal,0)),0) FROM SALES_INVOICE WHERE Lgr_Id={PID} AND Cmp_Code=1").fetchone()[0] or 0)
    td = float(cur.execute(f"SELECT ISNULL(SUM(ISNULL(Tran_Amount,0)),0) FROM TRAN_DETAIL WHERE Tran_Detail_Id={PID} AND Tran_DrCr='C' AND Cmp_Code=1").fetchone()[0] or 0)
    tm = float(cur.execute(f"SELECT ISNULL(SUM(ISNULL(Tran_Amount,0)),0) FROM TRAN_MASTER WHERE Tran_Master_Id={PID} AND Tran_DrCr='C' AND Cmp_Code=1").fetchone()[0] or 0)
    aj = float(cur.execute(f"SELECT ISNULL(SUM(ISNULL(CrAmount,0)),0) FROM AUTOJOURNAL WHERE Lgr_Id={PID} AND Cmp_Code=1").fetchone()[0] or 0)

    val = op + si - td - tm - aj
    print(f"  Opening        = {op:,.2f}")
    print(f"  Sales NetTotal = {si:,.2f}")
    print(f"  TRAN_DETAIL Cr = {td:,.2f}")
    print(f"  TRAN_MASTER Cr = {tm:,.2f}")
    print(f"  AUTOJOURNAL Cr = {aj:,.2f}")
    print(f"  ---")
    print(f"  OUR VALUE NOW  = {val:,.2f}")
    print(f"  Earlier ERP    = {EARLIER_ERP_READING:,.2f}")
    print(f"  Difference     = {val - EARLIER_ERP_READING:,.2f}")
    print()
    print(">>> Open RAM KIRTI outstanding in the ERP RIGHT NOW and compare to OUR VALUE NOW.")
    print(">>> If they match, the earlier 3,323 was just activity in between.\n")

    # Most recent bills
    print("--- 5 most recent SALES_INVOICE ---")
    for r in cur.execute(f"""SELECT TOP 5 Sal_Inv_Bill_No, CONVERT(varchar(19),Sal_Inv_Vdate,120), Sal_Inv_NetTotal
                             FROM SALES_INVOICE WHERE Lgr_Id={PID} AND Cmp_Code=1
                             ORDER BY Sal_Inv_Vdate DESC, Sal_Inv_Bill_No DESC""").fetchall():
        print(f"    Bill#{r[0]} {r[1]} amt={float(r[2] or 0):,.0f}")

    # Most recent credits (TRAN_DETAIL)
    print("\n--- 5 most recent TRAN_DETAIL credits (receipts) ---")
    try:
        for r in cur.execute(f"""SELECT TOP 5 Tran_Type, CONVERT(varchar(19),Tran_Date,120), Tran_Amount
                                 FROM TRAN_DETAIL WHERE Tran_Detail_Id={PID} AND Tran_DrCr='C' AND Cmp_Code=1
                                 ORDER BY Tran_Date DESC""").fetchall():
            print(f"    {str(r[0]).strip()} {r[1]} amt={float(r[2] or 0):,.0f}")
    except Exception as e:
        print(f"    ERR {str(e)[:80]}")

    c.close()
    print("\nDONE")


if __name__ == "__main__":
    main()
