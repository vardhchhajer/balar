"""
Verify balar_sync can read the previous year databases.
Also confirms AADI TEX gap closes when prior-year bills are included.
"""
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

SQL_SERVER   = os.getenv("SQL_SERVER",   "INDIASERVER")
SQL_USER     = os.getenv("SQL_USER",     "balar_sync")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "")

PREV_DBS = ["Acc2025_2026", "Acc2024_2025", "Acc2023_2024"]
CURR_DB  = "Acc2026_2027"
PID_AADI = 25469

def tryconn(db):
    cs = (f"DRIVER={{SQL Server}};SERVER={SQL_SERVER};DATABASE={db};"
          f"UID={SQL_USER};PWD={SQL_PASSWORD};ApplicationIntent=ReadOnly;")
    try:
        c = pyodbc.connect(cs, readonly=True, timeout=5)
        c.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
        return c, None
    except Exception as e:
        return None, str(e)[:80]

def main():
    print("=== Testing access to previous year databases ===\n")
    accessible = []
    for db in PREV_DBS:
        c, err = tryconn(db)
        if c:
            try:
                cur = c.cursor()
                cur.execute(f"SELECT COUNT(*) FROM PARTYDETAIL WHERE LGR_ID={PID_AADI} AND CMP_CODE=1")
                n = cur.fetchone()[0]
                print(f"  {db}: OK — PARTYDETAIL rows for AADI={n}")
                accessible.append((db, c))
            except Exception as e:
                print(f"  {db}: connected but can't read PARTYDETAIL: {str(e)[:60]}")
                c.close()
        else:
            print(f"  {db}: NO ACCESS — {err}")

    if not accessible:
        print("\nNo previous databases accessible yet. Grant access in SSMS first.")
        return

    # Now compute AADI outstanding including prior-year bills
    print(f"\n=== AADI TEX ({PID_AADI}) outstanding with prior-year data ===")
    TARGET = 435606.0

    # Current year
    cc, _ = tryconn(CURR_DB)
    cur_c = cc.cursor()

    bills_curr = float(cur_c.execute(f"SELECT ISNULL(SUM(ISNULL(BILL_AMOUNT,0)),0) FROM PARTYDETAIL WHERE LGR_ID={PID_AADI} AND CMP_CODE=1 AND JOBFLAG='S'").fetchone()[0] or 0)
    adj_curr   = float(cur_c.execute(f"SELECT ISNULL(SUM(ISNULL(ADJUSTAMT,0)+ISNULL(TOTAL,0)),0) FROM ADJMASTER WHERE Lgr_Id={PID_AADI} AND CMP_CODE=1").fetchone()[0] or 0)
    onacc_curr = float(cur_c.execute(f"""SELECT ISNULL(SUM(ISNULL(PARTAMOUNT,0)),0) FROM TRAN_DETAIL
                        WHERE Tran_Detail_Id={PID_AADI} AND CMP_CODE=1 AND TRAN_DRCR='C'
                          AND ISNULL(PARTAMOUNT,0)>0
                          AND (SHOWPARTAMT=1 OR SHOWPARTAMT IS NULL)
                          AND (REC_TRANS=0 OR REC_TRANS IS NULL)
                          AND TRAN_TYPE IN ('BR','CR','SR','YSR','BP','CP','DN','CN','J')""").fetchone()[0] or 0)
    onacc_m    = float(cur_c.execute(f"""SELECT ISNULL(SUM(ISNULL(TM.TRAN_AMOUNT,0)),0) FROM TRAN_MASTER TM
                        WHERE TM.Tran_Master_Id={PID_AADI} AND TM.CMP_CODE=1 AND TM.TRAN_DRCR='C'
                          AND TM.TRAN_TYPE IN ('SR','GCN','GDN')
                          AND EXISTS (SELECT 1 FROM TRAN_DETAIL TD WHERE TD.TRAN_ID=TM.TRAN_ID
                            AND TD.TRAN_TYPE=TM.TRAN_TYPE AND TD.CMP_CODE=TM.CMP_CODE
                            AND ISNULL(TD.PARTAMOUNT,0)>0)""").fetchone()[0] or 0)

    print(f"  Current year bills:  {bills_curr:,.0f}")
    print(f"  Current year adj:    {adj_curr:,.0f}")
    print(f"  Current year onacc:  {onacc_curr + onacc_m:,.0f}")

    bills_prev = 0.0
    adj_prev   = 0.0
    for db, conn in accessible:
        cur_p = conn.cursor()
        b = float(cur_p.execute(f"SELECT ISNULL(SUM(ISNULL(BILL_AMOUNT,0)),0) FROM PARTYDETAIL WHERE LGR_ID={PID_AADI} AND CMP_CODE=1 AND JOBFLAG='S'").fetchone()[0] or 0)
        a = float(cur_p.execute(f"SELECT ISNULL(SUM(ISNULL(ADJUSTAMT,0)+ISNULL(TOTAL,0)),0) FROM ADJMASTER WHERE Lgr_Id={PID_AADI} AND CMP_CODE=1").fetchone()[0] or 0)
        print(f"  {db}: bills={b:,.0f} adj={a:,.0f} net={b-a:,.0f}")
        bills_prev += b
        adj_prev   += a
        conn.close()
    cc.close()

    total_bills  = bills_curr + bills_prev
    total_adj    = adj_curr + adj_prev
    outstanding  = total_bills - total_adj - onacc_curr - onacc_m
    delta        = outstanding - TARGET
    print(f"\n  TOTAL: bills={total_bills:,.0f} adj={total_adj:,.0f} onacc={onacc_curr+onacc_m:,.0f}")
    print(f"  OUTSTANDING = {outstanding:,.0f}  (target={TARGET:,.0f}  delta={delta:,.0f})")
    print("  MATCH" if abs(delta) < 5000 else "  still off")

if __name__ == "__main__":
    main()
