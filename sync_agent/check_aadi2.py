"""
AADI TEX (25469): tracing the missing 236,250.
PENDING_AMOUNT=2,766,215, onaccD=2,094,359 → gap = 236,250 to reach 435,606.
Checking ADVANCE_ENTRY with looser filters, and PARTYDETAIL net.
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
TARGET = 435606.0


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
        return f"ERR:{str(e)[:60]}"


def main():
    c = conn()
    cur = c.cursor()

    # ADVANCE_ENTRY - all rows for this party
    print("--- ADVANCE_ENTRY all rows ---")
    cur.execute(f"""SELECT ENTRYTYPE, COUNT(*), SUM(ISNULL(AMOUNT,0)), SUM(ISNULL(PARTAMOUNT,0)),
                          MAX(CONVERT(varchar(10),VDATE,120))
                   FROM ADVANCE_ENTRY WHERE LGR_ID={PID} AND CMP_CODE=1
                   GROUP BY ENTRYTYPE""")
    rows = cur.fetchall()
    if not rows:
        print("  (none)")
    for r in rows:
        print(f"  {str(r[0] or '').strip():<8} n={r[1]} amt={float(r[2] or 0):,.0f} partamt={float(r[3] or 0):,.0f} maxdate={r[4]}")

    # TRAN_DETAIL - ALL credits (not just filtered)
    print("\n--- TRAN_DETAIL all credits (incl filtered-out ones) ---")
    cur.execute(f"""SELECT TRAN_TYPE, COUNT(*),
                          SUM(ISNULL(PARTAMOUNT,0)) AS partamt,
                          SUM(ISNULL(TRAN_AMOUNT,0)) AS tran_amt,
                          SUM(CASE WHEN (SHOWPARTAMT=1 OR SHOWPARTAMT IS NULL)
                                    AND (REC_TRANS=0 OR REC_TRANS IS NULL)
                                    AND TRAN_DRCR='C' THEN ISNULL(PARTAMOUNT,0) ELSE 0 END) AS filtered_partamt
                   FROM TRAN_DETAIL WHERE Tran_Detail_Id={PID} AND CMP_CODE=1 AND TRAN_DRCR='C'
                   GROUP BY TRAN_TYPE ORDER BY TRAN_TYPE""")
    for r in cur.fetchall():
        print(f"  {str(r[0]).strip():<6} n={r[1]:<4} partamt={float(r[2] or 0):,.0f} tran_amt={float(r[3] or 0):,.0f} filtered={float(r[4] or 0):,.0f}")

    # ONACCOUNT table
    print("\n--- ONACCOUNT table ---")
    oa_p = one(cur, f"SELECT SUM(ISNULL(PENDING,0)) FROM ONACCOUNT WHERE PARTY_ID={PID}")
    oa_c = one(cur, f"SELECT SUM(ISNULL(PARTCASHAMT,0)) FROM ONACCOUNT WHERE PARTY_ID={PID}")
    oa_a = one(cur, f"SELECT SUM(ISNULL(PARTADJAMT,0)) FROM ONACCOUNT WHERE PARTY_ID={PID}")
    print(f"  PENDING={oa_p} CASH={oa_c} ADJ={oa_a}")
    if all(isinstance(x, float) for x in [oa_p, oa_c, oa_a]):
        print(f"  ONACCOUNT net = {oa_p - oa_c - oa_a:,.0f}")

    # Try PENDING_AMOUNT as bills instead of BILL_AMOUNT
    pend = one(cur, f"SELECT SUM(ISNULL(PENDING_AMOUNT,0)) FROM PARTYDETAIL WHERE LGR_ID={PID} AND CMP_CODE=1 AND DATE<='{ASON}'")
    bills = one(cur, f"SELECT SUM(ISNULL(BILL_AMOUNT,0)) FROM PARTYDETAIL WHERE LGR_ID={PID} AND CMP_CODE=1 AND DATE<='{ASON}'")
    onacc_d = 2094359.0
    print(f"\n--- Pending-based formula ---")
    if isinstance(pend, float):
        out = pend - onacc_d
        print(f"  PENDING_AMOUNT({pend:,.0f}) - onaccD({onacc_d:,.0f}) = {out:,.0f}  (target={TARGET:,.0f} delta={out-TARGET:,.0f})")

    # check REC_TRANS filter effect
    print("\n--- TRAN_DETAIL BR rows with REC_TRANS != 0 ---")
    cur.execute(f"""SELECT COUNT(*), SUM(ISNULL(PARTAMOUNT,0))
                   FROM TRAN_DETAIL WHERE Tran_Detail_Id={PID} AND CMP_CODE=1
                     AND TRAN_TYPE='BR' AND REC_TRANS=1""")
    r = cur.fetchone()
    print(f"  n={r[0]} partamt={float(r[1] or 0):,.0f}")

    # SQLONACCOUNT1: debit-side partamount (BP/DN allocated to bills)
    print("\n--- SQLONACCOUNT1 equivalent: debit PARTAMOUNT (negative on-account) ---")
    neg = one(cur, f"""SELECT SUM(CASE WHEN TRAN_DRCR='C' THEN 0 ELSE 0-ISNULL(PARTAMOUNT,0) END)
                       FROM TRAN_DETAIL WHERE Tran_Detail_Id={PID} AND CMP_CODE=1
                         AND (SHOWPARTAMT=1 OR SHOWPARTAMT IS NULL)
                         AND TRAN_TYPE IN ('BR','CR','SR','YSR','BP','CP','DN','CN','J')""")
    print(f"  negative on-account (debit partamount) = {neg}")

    c.close()
    print("\nDONE")


if __name__ == "__main__":
    main()
