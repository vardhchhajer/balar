"""
AADI TEX (25469): final hunt for the 236,250 gap.
Try: exclude JR from PARTYDETAIL, check ADJMASTER date range,
check if 236,250 matches ONACCOUNT.ADJ, check ADJMASTER for PAID=False,
and check PARTYDETAIL PENDING_AMOUNT only for S flag.
"""
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

SQL_SERVER  = os.getenv("SQL_SERVER",  "INDIASERVER")
SQL_DATABASE= os.getenv("SQL_DATABASE","Acc2026_2027")
SQL_USER    = os.getenv("SQL_USER",    "balar_sync")
SQL_PASSWORD= os.getenv("SQL_PASSWORD","")

PID    = 25469
ASON   = "2026-07-31"
TARGET = 435606.0
ONACC  = 2094359.0

def conn():
    cs = (f"DRIVER={{SQL Server}};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};"
          f"UID={SQL_USER};PWD={SQL_PASSWORD};ApplicationIntent=ReadOnly;")
    c = pyodbc.connect(cs, readonly=True)
    c.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
    return c

def one(cur,sql):
    try:
        cur.execute(sql); r=cur.fetchone()
        return float(r[0]) if r and r[0] is not None else 0.0
    except Exception as e: return f"ERR:{str(e)[:60]}"

def main():
    c = conn(); cur = c.cursor()

    # bills excluding JR
    bills_S = one(cur, f"SELECT SUM(ISNULL(BILL_AMOUNT,0)) FROM PARTYDETAIL WHERE LGR_ID={PID} AND CMP_CODE=1 AND DATE<='{ASON}' AND JOBFLAG='S'")
    print(f"Bills (S only):           {bills_S:,.0f}")

    # adj all vs adj with PAID=1
    adj_all  = one(cur, f"SELECT SUM(ISNULL(ADJUSTAMT,0)) FROM ADJMASTER WHERE Lgr_Id={PID} AND CMP_CODE=1")
    adj_paid = one(cur, f"SELECT SUM(ISNULL(ADJUSTAMT,0)) FROM ADJMASTER WHERE Lgr_Id={PID} AND CMP_CODE=1 AND PAID=1")
    adj_tot  = one(cur, f"SELECT SUM(ISNULL(ADJUSTAMT,0)+ISNULL(TOTAL,0)) FROM ADJMASTER WHERE Lgr_Id={PID} AND CMP_CODE=1")
    print(f"ADJMASTER AdjustAmt all:  {adj_all:,.0f}")
    print(f"ADJMASTER AdjustAmt paid: {adj_paid:,.0f}")
    print(f"ADJMASTER Adj+Total:      {adj_tot:,.0f}")

    # ONACCOUNT ADJ - is it a separate receipt bucket?
    oa_adj = one(cur, f"SELECT SUM(ISNULL(PARTADJAMT,0)) FROM ONACCOUNT WHERE PARTY_ID={PID}")
    print(f"ONACCOUNT.PARTADJAMT:     {oa_adj:,.0f}")

    # ADJMASTER entries with PAID=False or NULL
    cur.execute(f"SELECT COUNT(*), SUM(ISNULL(ADJUSTAMT,0)) FROM ADJMASTER WHERE Lgr_Id={PID} AND CMP_CODE=1 AND (PAID=0 OR PAID IS NULL)")
    r = cur.fetchone(); print(f"ADJMASTER unpaid:         n={r[0]} adj={float(r[1] or 0):,.0f}")

    # All individual ADJMASTER rows
    print("\n--- All ADJMASTER rows ---")
    cur.execute(f"""SELECT TYPE, CONVERT(varchar(10),RECDATE,120), AMOUNT, ADJUSTAMT, TOTAL, DISCOUNT, PAID, BILLNO
                   FROM ADJMASTER WHERE Lgr_Id={PID} AND CMP_CODE=1
                   ORDER BY RECDATE, BILLNO""")
    rows = cur.fetchall()
    for r in rows[:15]:
        print(f"  {str(r[0]).strip():<4} {r[1]} bill={str(r[7]).strip():<6} amt={float(r[2] or 0):,.0f} adj={float(r[3] or 0):,.0f} tot={float(r[4] or 0):,.0f} disc={float(r[5] or 0):,.0f} paid={r[6]}")
    if len(rows)>15: print(f"  ... ({len(rows)-15} more rows)")

    # Try all candidate formulas
    print("\n--- Candidates (target=435,606, onaccD=2,094,359) ---")
    for label, bills, adj in [
        ("BillS  - Adj+Tot - onacc",  bills_S, adj_tot),
        ("BillAll- Adj+Tot - onacc",  bills_S+22500, adj_tot),
        ("BillS  - AdjOnly - onacc",  bills_S, adj_all),
        ("BillS  - AdjPaid - onacc",  bills_S, adj_paid),
        ("BillS  - Adj+Tot - onacc - oa_adj", bills_S, adj_tot),
    ]:
        if isinstance(bills,float) and isinstance(adj,float):
            extra = oa_adj if 'oa_adj' in label else 0.0
            out = bills - adj - ONACC - (oa_adj if 'oa_adj' in label else 0)
            print(f"  {label:<36} = {out:,.0f}  delta={out-TARGET:,.0f}")

    c.close()
    print("\nDONE")

if __name__=="__main__":
    main()
