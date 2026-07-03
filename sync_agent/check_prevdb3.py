"""
Diagnose why AADI (25469) prev-year on-account is 0.
Check what's in Acc2025_2026 TRAN_DETAIL for this party.
Also try using TRAN_AMOUNT instead of PARTAMOUNT for prev-year receipts.
"""
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

SQL_SERVER   = os.getenv("SQL_SERVER",   "INDIASERVER")
SQL_USER     = os.getenv("SQL_USER",     "balar_sync")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "")

PREV_DB = "Acc2025_2026"
CURR_DB = "Acc2026_2027"
PID     = 25469
TARGET  = 435606.0


def conn(db):
    cs = (f"DRIVER={{SQL Server}};SERVER={SQL_SERVER};DATABASE={db};"
          f"UID={SQL_USER};PWD={SQL_PASSWORD};ApplicationIntent=ReadOnly;")
    c = pyodbc.connect(cs, readonly=True)
    c.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
    return c


def main():
    cp = conn(PREV_DB)
    cc = conn(CURR_DB)
    cur_p = cp.cursor()
    cur_c = cc.cursor()

    print(f"=== Acc2025_2026 TRAN_DETAIL credits for party {PID} ===")
    cur_p.execute(f"""
        SELECT TRAN_TYPE, COUNT(*),
               SUM(ISNULL(TRAN_AMOUNT,0)) AS tran_amt,
               SUM(ISNULL(PARTAMOUNT,0)) AS part_amt,
               MAX(CAST(ISNULL(SHOWPARTAMT,0) AS INT)) AS max_show,
               MAX(CAST(ISNULL(REC_TRANS,0) AS INT)) AS max_rec
        FROM TRAN_DETAIL
        WHERE Tran_Detail_Id={PID} AND CMP_CODE=1 AND TRAN_DRCR='C'
        GROUP BY TRAN_TYPE ORDER BY SUM(ISNULL(TRAN_AMOUNT,0)) DESC
    """)
    for r in cur_p.fetchall():
        print(f"  {str(r[0]).strip():<6} n={r[1]:<4} tran={float(r[2] or 0):,.0f} part={float(r[3] or 0):,.0f} show={r[4]} rec={r[5]}")

    print(f"\n=== Acc2025_2026 TRAN_MASTER credits for party {PID} ===")
    cur_p.execute(f"""
        SELECT TRAN_TYPE, COUNT(*), SUM(ISNULL(TRAN_AMOUNT,0))
        FROM TRAN_MASTER WHERE Tran_Master_Id={PID} AND CMP_CODE=1 AND TRAN_DRCR='C'
        GROUP BY TRAN_TYPE ORDER BY SUM(ISNULL(TRAN_AMOUNT,0)) DESC
    """)
    for r in cur_p.fetchall():
        print(f"  {str(r[0]).strip():<6} n={r[1]:<4} sum={float(r[2] or 0):,.0f}")

    # Try PROC_OUTSTANDING's actual SQLONACCOUNT from prev DB:
    # It uses TRAN_AMOUNT directly (not PARTAMOUNT) for prior year on-account
    print(f"\n=== Trying TRAN_AMOUNT (not PARTAMOUNT) for prev-year onacc ===")
    onacc_tran = float(cur_p.execute(f"""
        SELECT ISNULL(SUM(ISNULL(TRAN_AMOUNT,0)),0) FROM TRAN_DETAIL
        WHERE Tran_Detail_Id={PID} AND CMP_CODE=1 AND TRAN_DRCR='C'
          AND TRAN_TYPE IN ('BR','CR','SR','YSR','BP','CP','DN','CN','J')
    """).fetchone()[0] or 0)
    print(f"  TRAN_AMOUNT sum = {onacc_tran:,.0f}")

    # Also check: does PROC_OUTSTANDING use Lgr_Op_Bal from prev year as opening?
    op = float(cur_p.execute(f"SELECT ISNULL(Lgr_Op_Bal,0) FROM LEDGER_DETAIL WHERE Lgr_Id={PID} AND Cmp_Code=1").fetchone()[0] or 0)
    opdr = str(cur_p.execute(f"SELECT Lgr_Op_DrCr FROM LEDGER_DETAIL WHERE Lgr_Id={PID} AND Cmp_Code=1").fetchone()[0] or "")
    print(f"\n=== Acc2025_2026 opening balance ===")
    print(f"  Lgr_Op_Bal={op:,.0f} ({opdr.strip()})")

    # Compute with prev TRAN_AMOUNT
    bills_c  = float(cur_c.execute(f"SELECT ISNULL(SUM(ISNULL(BILL_AMOUNT,0)),0) FROM PARTYDETAIL WHERE LGR_ID={PID} AND CMP_CODE=1 AND JOBFLAG='S'").fetchone()[0] or 0)
    adj_c    = float(cur_c.execute(f"SELECT ISNULL(SUM(ISNULL(ADJUSTAMT,0)+ISNULL(TOTAL,0)),0) FROM ADJMASTER WHERE Lgr_Id={PID} AND CMP_CODE=1").fetchone()[0] or 0)
    onacc_dc = float(cur_c.execute(f"""SELECT ISNULL(SUM(ISNULL(PARTAMOUNT,0)),0) FROM TRAN_DETAIL
        WHERE Tran_Detail_Id={PID} AND CMP_CODE=1 AND TRAN_DRCR='C'
          AND ISNULL(PARTAMOUNT,0)>0 AND (SHOWPARTAMT=1 OR SHOWPARTAMT IS NULL)
          AND (REC_TRANS=0 OR REC_TRANS IS NULL)
          AND TRAN_TYPE IN ('BR','CR','SR','YSR','BP','CP','DN','CN','J')""").fetchone()[0] or 0)
    bills_p  = float(cur_p.execute(f"SELECT ISNULL(SUM(ISNULL(BILL_AMOUNT,0)),0) FROM PARTYDETAIL WHERE LGR_ID={PID} AND CMP_CODE=1 AND JOBFLAG='S'").fetchone()[0] or 0)
    adj_p    = float(cur_p.execute(f"SELECT ISNULL(SUM(ISNULL(ADJUSTAMT,0)+ISNULL(TOTAL,0)),0) FROM ADJMASTER WHERE Lgr_Id={PID} AND CMP_CODE=1").fetchone()[0] or 0)

    out = bills_c + bills_p - adj_c - adj_p - onacc_dc - onacc_tran
    print(f"\n=== Formula with prev TRAN_AMOUNT ===")
    print(f"  bills_c={bills_c:,.0f} bills_p={bills_p:,.0f}")
    print(f"  adj_c={adj_c:,.0f} adj_p={adj_p:,.0f}")
    print(f"  onacc_curr={onacc_dc:,.0f} onacc_prev_tran={onacc_tran:,.0f}")
    print(f"  OUTSTANDING = {out:,.0f}  target={TARGET:,.0f}  delta={out-TARGET:,.0f}")
    print("  MATCH" if abs(out - TARGET) < 5000 else "  still off")

    cp.close()
    cc.close()
    print("\nDONE")


if __name__ == "__main__":
    main()
