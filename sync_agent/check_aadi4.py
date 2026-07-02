"""
AADI TEX (25469): bill-by-bill reconciliation.

For each bill in PARTYDETAIL, the outstanding = BILL_AMOUNT - ADJMASTER receipts.
The on-account (TRAN_DETAIL.PARTAMOUNT) are unallocated receipts that cover remaining bills.

Test:
  per_bill_pending = SUM(MAX(bill.BILL_AMOUNT - adj.ADJUSTAMT - adj.TOTAL, 0)) per VCODE+FLAG
  Then: per_bill_pending - unallocated_onaccount = outstanding
"""
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

SQL_SERVER   = os.getenv("SQL_SERVER",   "INDIASERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE", "Acc2026_2027")
SQL_USER     = os.getenv("SQL_USER",     "balar_sync")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "")

PID    = 25469
ASON   = "2026-07-31"
TARGET = 435606.0


def conn():
    cs = (f"DRIVER={{SQL Server}};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};"
          f"UID={SQL_USER};PWD={SQL_PASSWORD};ApplicationIntent=ReadOnly;")
    c = pyodbc.connect(cs, readonly=True)
    c.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
    return c


def main():
    c = conn()
    cur = c.cursor()

    # Per-bill pending: bill - adj receipts (floor at 0)
    cur.execute(f"""
        SELECT
            SUM(CASE WHEN pd.BILL_AMOUNT - ISNULL(am.adj,0) - ISNULL(am.tot,0) > 0
                     THEN pd.BILL_AMOUNT - ISNULL(am.adj,0) - ISNULL(am.tot,0)
                     ELSE 0 END) AS per_bill_pending
        FROM PARTYDETAIL pd
        LEFT JOIN (
            SELECT VCODE, FLAG, BillNo,
                   SUM(ISNULL(ADJUSTAMT,0)) AS adj,
                   SUM(ISNULL(TOTAL,0)) AS tot
            FROM ADJMASTER
            WHERE Lgr_Id={PID} AND CMP_CODE=1 AND RECDATE<='{ASON}'
            GROUP BY VCODE, FLAG, BillNo
        ) am ON am.VCODE=pd.VCODE AND am.FLAG=pd.JOBFLAG AND am.BillNo=pd.BILL_NO
        WHERE pd.LGR_ID={PID} AND pd.CMP_CODE=1 AND pd.DATE<='{ASON}'
          AND pd.JOBFLAG='S'
    """)
    per_bill = float(cur.fetchone()[0] or 0)

    # on-account: unallocated TRAN_DETAIL.PARTAMOUNT
    cur.execute(f"""SELECT SUM(ISNULL(PARTAMOUNT,0)) FROM TRAN_DETAIL
                   WHERE Tran_Detail_Id={PID} AND CMP_CODE=1 AND TRAN_DRCR='C'
                     AND ISNULL(PARTAMOUNT,0)>0
                     AND (SHOWPARTAMT=1 OR SHOWPARTAMT IS NULL)
                     AND (REC_TRANS=0 OR REC_TRANS IS NULL)
                     AND TRAN_TYPE IN ('BR','CR','SR','YSR','BP','CP','DN','CN','J')""")
    onacc = float(cur.fetchone()[0] or 0)

    # advances
    cur.execute(f"SELECT SUM(ISNULL(PARTAMOUNT,0)) FROM ADVANCE_ENTRY WHERE LGR_ID={PID} AND CMP_CODE=1")
    adv = float(cur.fetchone()[0] or 0)

    out = per_bill - onacc - adv
    print(f"Per-bill pending:  {per_bill:,.0f}")
    print(f"On-account (onacc):{onacc:,.0f}")
    print(f"Advance:           {adv:,.0f}")
    print(f"Outstanding:       {out:,.0f}  (target={TARGET:,.0f}  delta={out-TARGET:,.0f})")

    # Also try: PARTYDETAIL.PENDING_AMOUNT directly (pre-computed by ERP)
    cur.execute(f"""SELECT SUM(ISNULL(PENDING_AMOUNT,0)) FROM PARTYDETAIL
                   WHERE LGR_ID={PID} AND CMP_CODE=1 AND DATE<='{ASON}' AND JOBFLAG='S'""")
    pend_s = float(cur.fetchone()[0] or 0)
    out2 = pend_s - onacc - adv
    print(f"\nPENDING_AMOUNT(S): {pend_s:,.0f} - onacc({onacc:,.0f}) = {out2:,.0f}  delta={out2-TARGET:,.0f}")

    # Show unpaid bills (BILL_AMOUNT > adj+tot)
    print("\n--- Sample unpaid bills ---")
    cur.execute(f"""
        SELECT TOP 10 pd.BILL_NO, pd.BILL_AMOUNT,
               ISNULL(am.adj,0) AS adj, ISNULL(am.tot,0) AS tot,
               pd.BILL_AMOUNT - ISNULL(am.adj,0) - ISNULL(am.tot,0) AS pending,
               pd.PENDING_AMOUNT
        FROM PARTYDETAIL pd
        LEFT JOIN (
            SELECT VCODE, FLAG, BillNo, SUM(ISNULL(ADJUSTAMT,0)) AS adj, SUM(ISNULL(TOTAL,0)) AS tot
            FROM ADJMASTER WHERE Lgr_Id={PID} AND CMP_CODE=1 AND RECDATE<='{ASON}'
            GROUP BY VCODE, FLAG, BillNo
        ) am ON am.VCODE=pd.VCODE AND am.FLAG=pd.JOBFLAG AND am.BillNo=pd.BILL_NO
        WHERE pd.LGR_ID={PID} AND pd.CMP_CODE=1 AND pd.DATE<='{ASON}' AND pd.JOBFLAG='S'
          AND pd.BILL_AMOUNT - ISNULL(am.adj,0) - ISNULL(am.tot,0) > 0
        ORDER BY pd.DATE DESC, pd.BILL_NO
    """)
    for r in cur.fetchall():
        print(f"  bill={str(r[0]).strip():<8} amt={float(r[1] or 0):,.0f} adj={float(r[2] or 0):,.0f} tot={float(r[3] or 0):,.0f} pending={float(r[4] or 0):,.0f} PD_PENDING={float(r[5] or 0):,.0f}")

    c.close()
    print("\nDONE")


if __name__ == "__main__":
    main()
