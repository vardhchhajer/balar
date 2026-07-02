"""
Probe the round-number credits on MAHALAXMI (5141) and PRAGYA (7370).
List every credit >1 lakh with type/date/narration to identify what the
round crore-level credits actually are (contra / advance / bill-discount /
journal) so we know what to exclude from sales receivable.

Deltas to explain (ERP is HIGHER, we subtract too much):
    5141: +29,814,342
    7370: +11,504,114
"""
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

SQL_SERVER = os.getenv("SQL_SERVER", "INDIASERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE", "Acc2026_2027")
SQL_USER = os.getenv("SQL_USER", "balar_sync")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "")

PIDS = [5141, 7370]


def conn():
    cs = (
        f"DRIVER={{SQL Server}};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};"
        f"UID={SQL_USER};PWD={SQL_PASSWORD};ApplicationIntent=ReadOnly;"
    )
    c = pyodbc.connect(cs, readonly=True)
    c.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
    return c


def rows(cur, sql):
    try:
        cur.execute(sql)
        return cur.fetchall()
    except Exception as e:
        return [("ERR", str(e)[:100])]


def main():
    c = conn()
    cur = c.cursor()

    for pid in PIDS:
        print("=" * 64)
        print(f"PARTY {pid}")
        print("=" * 64)

        # Credits by type (TD)
        print("--- TRAN_DETAIL credits by Type ---")
        for r in rows(cur, f"""SELECT Tran_Type, COUNT(*), SUM(ISNULL(Tran_Amount,0))
                               FROM TRAN_DETAIL WHERE Tran_Detail_Id={pid} AND Tran_DrCr='C' AND Cmp_Code=1
                               GROUP BY Tran_Type ORDER BY SUM(ISNULL(Tran_Amount,0)) DESC"""):
            if r[0] == "ERR":
                print(f"  ERR {r[1]}"); break
            print(f"  {str(r[0]).strip():<6} n={r[1]:<4} sum={float(r[2] or 0):,.0f}")

        # Debits by type (TD)
        print("--- TRAN_DETAIL debits by Type ---")
        for r in rows(cur, f"""SELECT Tran_Type, COUNT(*), SUM(ISNULL(Tran_Amount,0))
                               FROM TRAN_DETAIL WHERE Tran_Detail_Id={pid} AND Tran_DrCr='D' AND Cmp_Code=1
                               GROUP BY Tran_Type ORDER BY SUM(ISNULL(Tran_Amount,0)) DESC"""):
            if r[0] == "ERR":
                print(f"  ERR {r[1]}"); break
            print(f"  {str(r[0]).strip():<6} n={r[1]:<4} sum={float(r[2] or 0):,.0f}")

        # Individual large credits with the master voucher type/date
        print("--- Individual credit lines > 100,000 (join master for type/date) ---")
        for r in rows(cur, f"""SELECT TOP 25 td.Tran_Type, tm.Tran_Type AS mtype,
                                      CONVERT(varchar(10), tm.Tran_Date, 120) AS dt,
                                      td.Tran_Amount, tm.Narration
                               FROM TRAN_DETAIL td
                               LEFT JOIN TRAN_MASTER tm ON td.Tran_ID = tm.Tran_ID AND td.Tran_Type = tm.Tran_Type AND td.Cmp_Code = tm.Cmp_Code
                               WHERE td.Tran_Detail_Id={pid} AND td.Tran_DrCr='C' AND td.Cmp_Code=1
                                 AND ISNULL(td.Tran_Amount,0) > 100000
                               ORDER BY td.Tran_Amount DESC"""):
            if r[0] == "ERR":
                print(f"  ERR {r[1]}"); break
            print(f"  tdtype={str(r[0]).strip():<5} mtype={str(r[1] or '').strip():<5} {r[2]} amt={float(r[3] or 0):,.0f} narr={str(r[4] or '')[:35]}")
        print()

    c.close()
    print("DONE")


if __name__ == "__main__":
    main()
