"""
Compute our outstanding formula for the TOP N parties by amount, so you can
compare many parties against the ERP's party-wise outstanding summary AT THE
SAME MOMENT. This distinguishes a systematic formula error (many parties off by
similar patterns) from sync-lag/timing (values match the ERP right now).

Formula = Opening + Sales_NetTotal - all credits (TRAN_DETAIL Cr + TRAN_MASTER Cr + AUTOJOURNAL Cr)

Run on INDIASERVER:
    cd C:\\Users\\Administrator\\Downloads\\sync_agent\\sync_agent
    py check_allparties.py
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

TOP_N = 25


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

    print(f"Query time: {datetime.now()}")
    print(f"Formula = Opening + Sales - all credits\n")

    # Compute outstanding for every party with sales orders in one set-based query
    cur.execute("""
        SELECT
            ld.Lgr_Id,
            lm.Lgr_name,
            ISNULL(ld.Lgr_Op_Bal, 0)
              + ISNULL((SELECT SUM(ISNULL(si.Sal_Inv_NetTotal,0)) FROM SALES_INVOICE si
                        WHERE si.Lgr_Id = ld.Lgr_Id AND si.Cmp_Code=1), 0)
              - ISNULL((SELECT SUM(ISNULL(td.Tran_Amount,0)) FROM TRAN_DETAIL td
                        WHERE td.Tran_Detail_Id = ld.Lgr_Id AND td.Tran_DrCr='C' AND td.Cmp_Code=1), 0)
              - ISNULL((SELECT SUM(ISNULL(tm.Tran_Amount,0)) FROM TRAN_MASTER tm
                        WHERE tm.Tran_Master_Id = ld.Lgr_Id AND tm.Tran_DrCr='C' AND tm.Cmp_Code=1), 0)
              - ISNULL((SELECT SUM(ISNULL(aj.CrAmount,0)) FROM AUTOJOURNAL aj
                        WHERE aj.Lgr_Id = ld.Lgr_Id AND aj.Cmp_Code=1), 0)
              AS outstanding
        FROM LEDGER_DETAIL ld
        JOIN LEDGER_MASTER lm ON ld.Lgr_Id = lm.Lgr_Id
        WHERE ld.Cmp_Code = 1
          AND ld.Lgr_Id IN (SELECT DISTINCT Lgr_Id FROM SALES_ORDER)
    """)
    rows = [(r[0], str(r[1] or "").strip(), float(r[2] or 0)) for r in cur.fetchall()]
    positive = [r for r in rows if r[2] > 0.5]
    positive.sort(key=lambda x: x[2], reverse=True)

    grand_total = sum(r[2] for r in positive)
    print(f"Parties with outstanding > 0: {len(positive)}")
    print(f"GRAND TOTAL outstanding: {grand_total:,.0f}\n")

    print(f"--- TOP {TOP_N} parties (compare each to ERP outstanding report NOW) ---")
    print(f"{'ID':<8}{'OUR VALUE':>16}   PARTY")
    for pid, name, val in positive[:TOP_N]:
        print(f"{pid:<8}{val:>16,.0f}   {name[:40]}")

    c.close()
    print("\nDONE")


if __name__ == "__main__":
    main()
