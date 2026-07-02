"""
Detail view of the FP and other small TRAN_MASTER credit entries for RAM KIRTI.
We need to understand which specific entries the ERP includes vs excludes.
"""
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

SQL_SERVER = os.getenv("SQL_SERVER", "INDIASERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE", "Acc2026_2027")
SQL_USER = os.getenv("SQL_USER", "balar_sync")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "")

PID = 20133


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

    print(f"=== ALL TRAN_MASTER Cr entries for party {PID} ===\n")
    cur.execute(f"""
        SELECT Tran_Type, Tran_Amount, CONVERT(varchar(10),Tran_Date,120) AS dt,
               Tran_DocNo, Narration
        FROM TRAN_MASTER
        WHERE Tran_Master_Id={PID} AND Tran_DrCr='C' AND Cmp_Code=1
        ORDER BY Tran_Type, Tran_Date
    """)
    total = 0.0
    for r in cur.fetchall():
        amt = float(r[1] or 0)
        total += amt
        print(f"  {str(r[0]).strip():<6} {r[2]} Doc#{r[3]} amt={amt:,.2f} narr={str(r[4] or '')[:50]}")
    print(f"\n  TOTAL TRAN_MASTER Cr = {total:,.2f}")

    # Also show TRAN_DETAIL credits by type for completeness
    print(f"\n=== TRAN_DETAIL Cr by Type ===")
    cur.execute(f"""
        SELECT Tran_Type, COUNT(*), SUM(ISNULL(Tran_Amount,0))
        FROM TRAN_DETAIL
        WHERE Tran_Detail_Id={PID} AND Tran_DrCr='C' AND Cmp_Code=1
        GROUP BY Tran_Type
    """)
    for r in cur.fetchall():
        print(f"  {str(r[0]).strip():<6} n={r[1]:<4} sum={float(r[2] or 0):,.2f}")

    # What's the J type amount?
    print(f"\n=== TRAN_DETAIL 'J' entries (journals) ===")
    cur.execute(f"""
        SELECT Tran_Amount, CONVERT(varchar(10),Tran_Date,120), Tran_DocNo
        FROM TRAN_DETAIL
        WHERE Tran_Detail_Id={PID} AND Tran_DrCr='C' AND Cmp_Code=1 AND Tran_Type='J'
        ORDER BY Tran_Date
    """)
    for r in cur.fetchall():
        print(f"  {r[1]} Doc#{r[2]} amt={float(r[0] or 0):,.2f}")

    c.close()
    print("\nDONE")


if __name__ == "__main__":
    main()
