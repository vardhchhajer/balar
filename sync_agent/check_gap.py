"""
Diagnostic: find what makes up the ~614,140 gap between our ONACCOUNT
outstanding and the ERP's TOTAL NET DUE for RAM KIRTI PVT LTD (party 20133).

ERP shows:            48,062,253
ONACCOUNT formula:    48,676,393  (PENDING 59,015,061 - CASH 0 - ADJ 10,338,668)
Gap to explain:          614,140

Run on INDIASERVER:
    cd C:\\Users\\Administrator\\Downloads\\sync_agent\\sync_agent
    py check_gap.py
Then paste the full output back.
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
TARGET = 48062253.0
ONACCOUNT_RESULT = 48676393.0
GAP = ONACCOUNT_RESULT - TARGET  # 614,140


def conn():
    cs = (
        f"DRIVER={{SQL Server}};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};"
        f"UID={SQL_USER};PWD={SQL_PASSWORD};ApplicationIntent=ReadOnly;"
    )
    c = pyodbc.connect(cs, readonly=True)
    c.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
    return c


def scalar(cur, sql, default=0.0):
    try:
        cur.execute(sql)
        row = cur.fetchone()
        return float(row[0]) if row and row[0] is not None else default
    except Exception as e:
        return f"ERR: {str(e)[:80]}"


def main():
    c = conn()
    cur = c.cursor()

    print(f"=== GAP TO EXPLAIN for party {PARTY}: {GAP:,.0f} ===\n")

    # 1) Re-confirm ONACCOUNT breakdown
    print("--- ONACCOUNT ---")
    pend = scalar(cur, f"SELECT SUM(ISNULL(PENDING,0)) FROM ONACCOUNT WHERE PARTY_ID={PARTY}")
    cash = scalar(cur, f"SELECT SUM(ISNULL(PARTCASHAMT,0)) FROM ONACCOUNT WHERE PARTY_ID={PARTY}")
    adj = scalar(cur, f"SELECT SUM(ISNULL(PARTADJAMT,0)) FROM ONACCOUNT WHERE PARTY_ID={PARTY}")
    print(f"  PENDING     = {pend}")
    print(f"  PARTCASHAMT = {cash}")
    print(f"  PARTADJAMT  = {adj}")
    if isinstance(pend, float):
        print(f"  PENDING - CASH - ADJ = {pend - cash - adj:,.0f}\n")

    # 2) ADJMASTER settlement deductions for this party (discount / otherless / interest / adjust)
    print("--- ADJMASTER (settlement deductions) ---")
    for col in ["Discount", "OtherLess", "Interest", "IntRec", "AdjustAmt", "Amount", "Total"]:
        v = scalar(cur, f"SELECT SUM(ISNULL({col},0)) FROM ADJMASTER WHERE Lgr_Id={PARTY}")
        print(f"  SUM({col}) = {v}")
    disc_other = scalar(cur, f"SELECT SUM(ISNULL(Discount,0)+ISNULL(OtherLess,0)) FROM ADJMASTER WHERE Lgr_Id={PARTY}")
    print(f"  >>> Discount+OtherLess = {disc_other}   (does this ~= {GAP:,.0f}?)\n")

    # 3) ADJMASTER for current company only (cmp_code = 1)
    print("--- ADJMASTER (cmp_code=1 only) ---")
    disc_other_cmp = scalar(cur, f"SELECT SUM(ISNULL(Discount,0)+ISNULL(OtherLess,0)) FROM ADJMASTER WHERE Lgr_Id={PARTY} AND Cmp_Code=1")
    print(f"  Discount+OtherLess (cmp=1) = {disc_other_cmp}   (does this ~= {GAP:,.0f}?)\n")

    # 4) ADJUSTMENTVOUCHER_BILLDETAIL deductions
    print("--- ADJUSTMENTVOUCHER_BILLDETAIL ---")
    try:
        cur.execute("SELECT TOP 0 * FROM ADJUSTMENTVOUCHER_BILLDETAIL")
        avcols = [d[0] for d in cur.description]
        print(f"  columns: {avcols}")
        for col in avcols:
            low = col.lower()
            if any(k in low for k in ["disc", "less", "interest", "adjust", "amount", "total", "rd", "sweet"]):
                v = scalar(cur, f"SELECT SUM(ISNULL([{col}],0)) FROM ADJUSTMENTVOUCHER_BILLDETAIL WHERE LGR_ID={PARTY}")
                print(f"  SUM({col}) = {v}")
    except Exception as e:
        print(f"  ERR: {str(e)[:120]}")
    print()

    # 5) Count of ONACCOUNT rows with tiny/negative net (maybe ERP floors each bill at 0)
    print("--- ONACCOUNT per-row net analysis ---")
    neg = scalar(cur, f"SELECT SUM(CASE WHEN (ISNULL(PENDING,0)-ISNULL(PARTCASHAMT,0)-ISNULL(PARTADJAMT,0)) < 0 THEN (ISNULL(PENDING,0)-ISNULL(PARTCASHAMT,0)-ISNULL(PARTADJAMT,0)) ELSE 0 END) FROM ONACCOUNT WHERE PARTY_ID={PARTY}")
    print(f"  Sum of NEGATIVE per-row nets = {neg}   (if ERP floors at 0, adds back {GAP:,.0f}?)")
    floored = scalar(cur, f"SELECT SUM(CASE WHEN (ISNULL(PENDING,0)-ISNULL(PARTCASHAMT,0)-ISNULL(PARTADJAMT,0)) > 0 THEN (ISNULL(PENDING,0)-ISNULL(PARTCASHAMT,0)-ISNULL(PARTADJAMT,0)) ELSE 0 END) FROM ONACCOUNT WHERE PARTY_ID={PARTY}")
    print(f"  Sum of POSITIVE per-row nets only (floor<0 at 0) = {floored}   (does this ~= {TARGET:,.0f}?)\n")

    c.close()
    print("DONE")


if __name__ == "__main__":
    main()
