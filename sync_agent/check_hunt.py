"""
Hunt for the fixed ~3,323 difference on RAM KIRTI (party 20133).
Our value is 3,323 LOWER than the ERP -> we likely subtract a credit the ERP
outstanding report ignores (contra / TDS / round-off / journal).

Run on INDIASERVER:
    cd C:\\Users\\Administrator\\Downloads\\sync_agent\\sync_agent
    py check_hunt.py
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
GAP = 3323.0


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
        return [("ERR", str(e)[:90])]


def main():
    c = conn()
    cur = c.cursor()

    print(f"=== Hunting the {GAP:,.0f} gap for party {PID} ===\n")

    # 1) TRAN_DETAIL credits grouped by type — is there a non-receipt credit type?
    print("--- TRAN_DETAIL credits by Tran_Type ---")
    for r in rows(cur, f"""SELECT Tran_Type, COUNT(*), SUM(ISNULL(Tran_Amount,0))
                           FROM TRAN_DETAIL
                           WHERE Tran_Detail_Id={PID} AND Tran_DrCr='C' AND Cmp_Code=1
                           GROUP BY Tran_Type ORDER BY Tran_Type"""):
        if r[0] == "ERR":
            print(f"  ERR {r[1]}"); break
        flag = "  <== ~3323?" if abs(float(r[2] or 0) - GAP) < 50 else ""
        print(f"  {str(r[0]).strip():<6} n={r[1]:<4} sum={float(r[2] or 0):,.2f}{flag}")
    print()

    # 2) Any single credit entry near 3,323
    print("--- TRAN_DETAIL credit entries within 100 of 3,323 ---")
    found = rows(cur, f"""SELECT Tran_Type, Tran_Amount FROM TRAN_DETAIL
                          WHERE Tran_Detail_Id={PID} AND Tran_DrCr='C' AND Cmp_Code=1
                            AND ABS(ISNULL(Tran_Amount,0) - {GAP}) < 100""")
    if not found:
        print("  (none)")
    for r in found:
        if r[0] == "ERR":
            print(f"  ERR {r[1]}"); break
        print(f"  {str(r[0]).strip()} amt={float(r[1] or 0):,.2f}")
    print()

    # 3) TDS entries (common cause) — check ADJMASTER TDS column and any TDS ledger
    print("--- ADJMASTER TDS / small columns for party ---")
    for col in ["TDS_AMOUNT", "Discount", "OtherLess", "Interest", "IntRec"]:
        r = rows(cur, f"SELECT SUM(ISNULL({col},0)) FROM ADJMASTER WHERE Lgr_Id={PID} AND Cmp_Code=1")
        if r and r[0][0] != "ERR":
            v = float(r[0][0] or 0)
            flag = "  <== ~3323?" if abs(v - GAP) < 50 else ""
            print(f"  ADJMASTER.{col} = {v:,.2f}{flag}")
        else:
            print(f"  ADJMASTER.{col} = n/a")
    print()

    # 4) Round-off: does the ERP outstanding maybe exclude round-off credits?
    print("--- Look for 'ROUND' or 'TDS' in credit narrations (TRAN_MASTER) ---")
    for r in rows(cur, f"""SELECT TOP 20 Tran_Type, Tran_Amount, Narration
                           FROM TRAN_MASTER
                           WHERE Tran_Master_Id={PID} AND Tran_DrCr='C' AND Cmp_Code=1
                             AND (Narration LIKE '%ROUND%' OR Narration LIKE '%TDS%' OR ABS(ISNULL(Tran_Amount,0)-{GAP})<100)"""):
        if r[0] == "ERR":
            print(f"  ERR {r[1]}"); break
        print(f"  {str(r[0]).strip()} amt={float(r[1] or 0):,.2f} narr={str(r[2] or '')[:40]}")
    print()

    # 5) Recompute excluding each credit type to see which yields exactly ERP value
    print("--- Credit totals by source (for manual check) ---")
    td = float(rows(cur, f"SELECT ISNULL(SUM(ISNULL(Tran_Amount,0)),0) FROM TRAN_DETAIL WHERE Tran_Detail_Id={PID} AND Tran_DrCr='C' AND Cmp_Code=1")[0][0] or 0)
    tm = float(rows(cur, f"SELECT ISNULL(SUM(ISNULL(Tran_Amount,0)),0) FROM TRAN_MASTER WHERE Tran_Master_Id={PID} AND Tran_DrCr='C' AND Cmp_Code=1")[0][0] or 0)
    print(f"  TRAN_DETAIL Cr total = {td:,.2f}")
    print(f"  TRAN_MASTER Cr total = {tm:,.2f}")

    c.close()
    print("\nDONE")


if __name__ == "__main__":
    main()
