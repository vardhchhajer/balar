"""
AADI TEX (25469) is off by 236,250. We get 671,856 but target is 435,606.
We need to subtract 236,250 more. Explore PARTYDETAIL structure for this party.
"""
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

SQL_SERVER = os.getenv("SQL_SERVER", "INDIASERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE", "Acc2026_2027")
SQL_USER = os.getenv("SQL_USER", "balar_sync")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "")

PID = 25469
ASON = "2026-07-31"


def conn():
    cs = (f"DRIVER={{SQL Server}};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};"
          f"UID={SQL_USER};PWD={SQL_PASSWORD};ApplicationIntent=ReadOnly;")
    c = pyodbc.connect(cs, readonly=True)
    c.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
    return c


def main():
    c = conn()
    cur = c.cursor()

    # PARTYDETAIL breakdown by JOBFLAG
    print("--- PARTYDETAIL by JOBFLAG ---")
    cur.execute(f"""SELECT JOBFLAG, COUNT(*),
                          SUM(ISNULL(BILL_AMOUNT,0)) AS bills,
                          SUM(ISNULL(PENDING_AMOUNT,0)) AS pending
                   FROM PARTYDETAIL WHERE LGR_ID={PID} AND CMP_CODE=1 AND DATE<='{ASON}'
                   GROUP BY JOBFLAG ORDER BY JOBFLAG""")
    for r in cur.fetchall():
        print(f"  {str(r[0]).strip():<8} n={r[1]:<4} BILL_AMOUNT={float(r[2] or 0):,.0f}  PENDING_AMOUNT={float(r[3] or 0):,.0f}")

    # What's the sum if we use PENDING_AMOUNT instead of BILL_AMOUNT?
    print("\n--- PARTYDETAIL SUM(PENDING_AMOUNT) vs SUM(BILL_AMOUNT) ---")
    cur.execute(f"SELECT SUM(ISNULL(BILL_AMOUNT,0)), SUM(ISNULL(PENDING_AMOUNT,0)) FROM PARTYDETAIL WHERE LGR_ID={PID} AND CMP_CODE=1 AND DATE<='{ASON}'")
    r = cur.fetchone()
    ba = float(r[0] or 0); pa = float(r[1] or 0)
    print(f"  BILL_AMOUNT={ba:,.0f}  PENDING_AMOUNT={pa:,.0f}  diff={ba-pa:,.0f}")

    # ADJMASTER breakdown
    print("\n--- ADJMASTER breakdown ---")
    cur.execute(f"""SELECT TYPE, COUNT(*), SUM(ISNULL(ADJUSTAMT,0)), SUM(ISNULL(TOTAL,0)),
                          SUM(ISNULL(AMOUNT,0)), SUM(ISNULL(DISCOUNT,0))
                   FROM ADJMASTER WHERE Lgr_Id={PID} AND CMP_CODE=1 AND RECDATE<='{ASON}'
                   GROUP BY TYPE ORDER BY TYPE""")
    for r in cur.fetchall():
        print(f"  {str(r[0]).strip():<6} n={r[1]:<4} AdjAmt={float(r[2] or 0):,.0f} Total={float(r[3] or 0):,.0f} Amount={float(r[4] or 0):,.0f} Disc={float(r[5] or 0):,.0f}")

    # Paid flag in ADJMASTER
    print("\n--- ADJMASTER PAID flag distribution ---")
    cur.execute(f"SELECT PAID, COUNT(*), SUM(ISNULL(ADJUSTAMT,0)) FROM ADJMASTER WHERE Lgr_Id={PID} AND CMP_CODE=1 GROUP BY PAID")
    for r in cur.fetchall():
        print(f"  PAID={r[0]} n={r[1]} sum={float(r[2] or 0):,.0f}")

    # TRAN_MASTER Cr entries
    print("\n--- TRAN_MASTER Cr entries (all types) ---")
    cur.execute(f"""SELECT TRAN_TYPE, COUNT(*), SUM(ISNULL(TRAN_AMOUNT,0))
                   FROM TRAN_MASTER WHERE Tran_Master_Id={PID} AND CMP_CODE=1 AND TRAN_DRCR='C'
                   GROUP BY TRAN_TYPE""")
    rows = cur.fetchall()
    if not rows:
        print("  (none)")
    for r in rows:
        print(f"  {str(r[0]).strip():<6} n={r[1]:<4} sum={float(r[2] or 0):,.0f}")

    # Candidate formulas
    adj_adj = float(cur.execute(f"SELECT SUM(ISNULL(ADJUSTAMT,0)) FROM ADJMASTER WHERE Lgr_Id={PID} AND CMP_CODE=1").fetchone()[0] or 0)
    adj_amt = float(cur.execute(f"SELECT SUM(ISNULL(Amount,0)) FROM ADJMASTER WHERE Lgr_Id={PID} AND CMP_CODE=1").fetchone()[0] or 0)
    onacc = 2094359.0
    bills = 6680528.0

    print(f"\n--- Candidate formulas (target=435,606) ---")
    print(f"  bills - AdjustAmt - onaccD         = {bills - adj_adj - onacc:,.0f}")
    print(f"  bills - Amount    - onaccD         = {bills - adj_amt - onacc:,.0f}")

    c.close()
    print("\nDONE")


if __name__ == "__main__":
    main()
