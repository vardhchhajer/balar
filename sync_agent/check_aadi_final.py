"""
Final AADI check: compare PROC_OUTSTANDING result vs ledger formula,
and check what @CriteriaType=1 means for AADI specifically.

The PROC_OUTSTANDING call was:
  exec PROC_OUTSTANDING N'1',N'Acc2026_2027.Dbo.',1,2,N'##9716',N'03/Jul/2026',1,0,N'0',N'Acc2025_2026.Dbo.'

@CriteriaType=1 means: show parties where outstanding > 0
@GroupType=2 means: Sundry Debtors

The proc builds the outstanding using PARTYDETAIL bills - ADJMASTER - on-account.
For AADI, all BR receipts have PARTAMOUNT=0 (fully allocated to bills via ADJMASTER).
The "on-account" bucket should therefore be 0 for AADI's current-year receipts...
but we see onacc_dc=2,094,359.

This final check: what is that 2,094,359 actually made up of?
Are those receipts in ADJMASTER too (double-counted)?
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

    # The 2,094,359 on-account: break down by TRAN_ID to see if these
    # receipts are ALSO in ADJMASTER (which would mean double-counting)
    print("=== Current-year BR receipts with PARTAMOUNT > 0 ===")
    cur.execute(f"""
        SELECT TOP 10 TD.TRAN_ID, TD.TRAN_AMOUNT, TD.PARTAMOUNT, TD.SHOWPARTAMT,
               ISNULL(TD.REC_TRANS,0) AS rec_trans,
               (SELECT SUM(ISNULL(AM.ADJUSTAMT,0)) FROM ADJMASTER AM
                WHERE AM.Lgr_Id={PID} AND AM.CMP_CODE=1 AND AM.VCODE=TD.TRAN_ID) AS in_adjmaster
        FROM TRAN_DETAIL TD
        WHERE TD.Tran_Detail_Id={PID} AND TD.CMP_CODE=1 AND TD.TRAN_DRCR='C'
          AND ISNULL(TD.PARTAMOUNT,0)>0 AND TD.TRAN_TYPE='BR'
        ORDER BY TD.TRAN_AMOUNT DESC
    """)
    total_also_in_adj = 0.0
    total_partamt = 0.0
    for r in cur.fetchall():
        in_adj = float(r[5] or 0)
        partamt = float(r[2] or 0)
        total_also_in_adj += in_adj
        total_partamt += partamt
        print(f"  TRAN_ID={r[0]} tran={float(r[1] or 0):,.0f} part={partamt:,.0f} show={r[3]} rec={r[4]} in_adjmaster={in_adj:,.0f}")

    print(f"\n  SUM PARTAMOUNT (first 10) = {total_partamt:,.0f}")
    print(f"  SUM also in ADJMASTER    = {total_also_in_adj:,.0f}")

    # Total PARTAMOUNT all rows
    total_pa = float(cur.execute(f"""SELECT SUM(ISNULL(PARTAMOUNT,0)) FROM TRAN_DETAIL
        WHERE Tran_Detail_Id={PID} AND CMP_CODE=1 AND TRAN_DRCR='C'
          AND ISNULL(PARTAMOUNT,0)>0 AND (SHOWPARTAMT=1 OR SHOWPARTAMT IS NULL)
          AND (REC_TRANS=0 OR REC_TRANS IS NULL) AND TRAN_TYPE='BR'""").fetchone()[0] or 0)

    # How much of the PARTAMOUNT is ALSO captured in ADJMASTER?
    # If a receipt's PARTAMOUNT is in ADJMASTER, we're double-subtracting
    adj_from_partamt_receipts = float(cur.execute(f"""
        SELECT SUM(ISNULL(AM.ADJUSTAMT,0))
        FROM ADJMASTER AM
        WHERE AM.Lgr_Id={PID} AND AM.CMP_CODE=1
          AND AM.VCODE IN (
              SELECT TRAN_ID FROM TRAN_DETAIL
              WHERE Tran_Detail_Id={PID} AND CMP_CODE=1 AND TRAN_DRCR='C'
                AND ISNULL(PARTAMOUNT,0)>0 AND TRAN_TYPE='BR'
          )
    """).fetchone()[0] or 0)

    print(f"\n  Total PARTAMOUNT in onacc bucket = {total_pa:,.0f}")
    print(f"  ADJMASTER amount for same receipts = {adj_from_partamt_receipts:,.0f}")
    print(f"  These receipts are {'ALSO' if adj_from_partamt_receipts > 0 else 'NOT'} in ADJMASTER")

    # If we DON'T subtract these (they're already in adj), what's the outstanding?
    bills = float(cur.execute(f"SELECT ISNULL(SUM(ISNULL(BILL_AMOUNT,0)),0) FROM PARTYDETAIL WHERE LGR_ID={PID} AND CMP_CODE=1 AND JOBFLAG='S'").fetchone()[0] or 0)
    adj   = float(cur.execute(f"SELECT ISNULL(SUM(ISNULL(ADJUSTAMT,0)+ISNULL(TOTAL,0)),0) FROM ADJMASTER WHERE Lgr_Id={PID} AND CMP_CODE=1").fetchone()[0] or 0)

    print(f"\n  IF we exclude the double-counted on-account:")
    out_no_double = bills - adj
    print(f"  bills({bills:,.0f}) - adj({adj:,.0f}) = {out_no_double:,.0f}  delta={out_no_double-TARGET:,.0f}")

    c.close()
    print("\nDONE")


if __name__ == "__main__":
    main()
