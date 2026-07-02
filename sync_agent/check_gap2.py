"""
Diagnostic #2 for the 614,140 gap on RAM KIRTI (party 20133).

Findings so far:
  ONACCOUNT PENDING           = 59,015,061
  ONACCOUNT PARTADJAMT        = 10,338,668  (on separate rows from PENDING)
  Our formula (PEND-CASH-ADJ) = 48,676,393
  ERP TOTAL NET DUE           = 48,062,253
  ERP deducts total           = 10,952,808  (= 59,015,061 - 48,062,253)
  We deduct                   = 10,338,668
  MISSING credit to find      =    614,140

Hypothesis: the 614,140 is a credit note (GCN/incentive), sales return (SR),
or a receipt posted after the ONACCOUNT snapshot. This checks the party's
credit-side ledger entries by type, and also checks the ONACCOUNT snapshot date(s).

Run on INDIASERVER:
    cd C:\\Users\\Administrator\\Downloads\\sync_agent\\sync_agent
    py check_gap2.py
Paste the full output back.
"""
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

SQL_SERVER = os.getenv("SQL_SERVER", "INDIASERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE", "Acc2026_2027")
SQL_USER = os.getenv("SQL_USER", "balar_sync")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "")

PARTY = 20133
MISSING = 614140.0


def conn():
    cs = (
        f"DRIVER={{SQL Server}};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};"
        f"UID={SQL_USER};PWD={SQL_PASSWORD};ApplicationIntent=ReadOnly;"
    )
    c = pyodbc.connect(cs, readonly=True)
    c.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
    return c


def run(cur, sql):
    cur.execute(sql)
    return cur.fetchall()


def main():
    c = conn()
    cur = c.cursor()
    print(f"=== Looking for the missing credit of {MISSING:,.0f} (party {PARTY}) ===\n")

    # A) ONACCOUNT snapshot date(s) — is it stale / multi-dated?
    print("--- ONACCOUNT snapshot dates ---")
    try:
        rows = run(cur, f"""
            SELECT CONVERT(varchar(10), [DATE], 120) AS d,
                   COUNT(*) AS rows,
                   SUM(ISNULL(PENDING,0)) AS pend,
                   SUM(ISNULL(PARTADJAMT,0)) AS adj
            FROM ONACCOUNT WHERE PARTY_ID={PARTY}
            GROUP BY CONVERT(varchar(10), [DATE], 120)
            ORDER BY d
        """)
        for r in rows:
            print(f"  {r[0]} | rows={r[1]} | PENDING={float(r[2] or 0):,.0f} | ADJ={float(r[3] or 0):,.0f}")
    except Exception as e:
        print(f"  ERR: {str(e)[:120]}")
    print()

    # B) TRAN_MASTER credit-side entries by type (party = Tran_Master_Id)
    print("--- TRAN_MASTER credits (Tran_Master_Id = party) by type ---")
    try:
        rows = run(cur, f"""
            SELECT Tran_type, Tran_DrCr, COUNT(*) AS n, SUM(ISNULL(Tran_Amount,0)) AS amt
            FROM TRAN_MASTER
            WHERE Tran_Master_Id={PARTY}
            GROUP BY Tran_type, Tran_DrCr
            ORDER BY Tran_type, Tran_DrCr
        """)
        for r in rows:
            flag = "  <== ~614k?" if abs(float(r[3] or 0) - MISSING) < 5000 else ""
            print(f"  type={r[0]:<5} drcr={r[1]} n={r[2]:<4} amt={float(r[3] or 0):,.0f}{flag}")
    except Exception as e:
        print(f"  ERR: {str(e)[:120]}")
    print()

    # C) Credit notes (GCN) and sales returns (SR) specifically, current year
    print("--- Credit-side totals (all Cr entries) for party ---")
    try:
        rows = run(cur, f"""
            SELECT Tran_type, SUM(ISNULL(Tran_Amount,0)) AS amt
            FROM TRAN_MASTER
            WHERE Tran_Master_Id={PARTY} AND Tran_DrCr='C'
            GROUP BY Tran_type ORDER BY amt DESC
        """)
        tot = 0.0
        for r in rows:
            amt = float(r[1] or 0)
            tot += amt
            print(f"  {r[0]:<6} = {amt:,.0f}")
        print(f"  TOTAL Cr = {tot:,.0f}")
    except Exception as e:
        print(f"  ERR: {str(e)[:120]}")
    print()

    # D) Scan any single TRAN_MASTER row near 614,140 for this party
    print("--- Any single TRAN_MASTER entry near 614,140 ---")
    try:
        rows = run(cur, f"""
            SELECT Tran_type, Tran_DrCr, CONVERT(varchar(10),Tran_Date,120), Tran_Amount
            FROM TRAN_MASTER
            WHERE Tran_Master_Id={PARTY}
              AND ABS(ISNULL(Tran_Amount,0) - {MISSING}) < 20000
            ORDER BY Tran_Date
        """)
        if not rows:
            print("  (none within 20k)")
        for r in rows:
            print(f"  type={r[0]} drcr={r[1]} date={r[2]} amt={float(r[3] or 0):,.0f}")
    except Exception as e:
        print(f"  ERR: {str(e)[:120]}")

    c.close()
    print("\nDONE")


if __name__ == "__main__":
    main()
