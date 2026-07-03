"""
Check AADI TEX outstanding including BOTH bills AND receipts from previous year.
PROC_OUTSTANDING passes PrevDB='Acc2025_2026.Dbo.' only (one year back).
So we include PARTYDETAIL bills + ADJMASTER adj + TRAN_DETAIL onacc from Acc2025_2026.
"""
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

SQL_SERVER   = os.getenv("SQL_SERVER",   "INDIASERVER")
SQL_USER     = os.getenv("SQL_USER",     "balar_sync")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "")

CURR_DB = "Acc2026_2027"
PREV_DB = "Acc2025_2026"   # only one year back per PROC_OUTSTANDING call
PID     = 25469
TARGET  = 435606.0


def conn(db):
    cs = (f"DRIVER={{SQL Server}};SERVER={SQL_SERVER};DATABASE={db};"
          f"UID={SQL_USER};PWD={SQL_PASSWORD};ApplicationIntent=ReadOnly;")
    c = pyodbc.connect(cs, readonly=True)
    c.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
    return c


def get_bills(cur, pid):
    return float(cur.execute(f"SELECT ISNULL(SUM(ISNULL(BILL_AMOUNT,0)),0) FROM PARTYDETAIL WHERE LGR_ID={pid} AND CMP_CODE=1 AND JOBFLAG='S'").fetchone()[0] or 0)


def get_adj(cur, pid):
    return float(cur.execute(f"SELECT ISNULL(SUM(ISNULL(ADJUSTAMT,0)+ISNULL(TOTAL,0)+ISNULL(INTEREST,0)-ISNULL(INTREC,0)),0) FROM ADJMASTER WHERE Lgr_Id={pid} AND CMP_CODE=1").fetchone()[0] or 0)


def get_onacc_d(cur, pid):
    return float(cur.execute(f"""SELECT ISNULL(SUM(ISNULL(PARTAMOUNT,0)),0) FROM TRAN_DETAIL
        WHERE Tran_Detail_Id={pid} AND CMP_CODE=1 AND TRAN_DRCR='C'
          AND ISNULL(PARTAMOUNT,0)>0
          AND (SHOWPARTAMT=1 OR SHOWPARTAMT IS NULL)
          AND (REC_TRANS=0 OR REC_TRANS IS NULL)
          AND TRAN_TYPE IN ('BR','CR','SR','YSR','BP','CP','DN','CN','J')""").fetchone()[0] or 0)


def get_onacc_m(cur, pid):
    return float(cur.execute(f"""SELECT ISNULL(SUM(ISNULL(TM.TRAN_AMOUNT,0)),0) FROM TRAN_MASTER TM
        WHERE TM.Tran_Master_Id={pid} AND TM.CMP_CODE=1 AND TM.TRAN_DRCR='C'
          AND TM.TRAN_TYPE IN ('SR','GCN','GDN')
          AND EXISTS (SELECT 1 FROM TRAN_DETAIL TD WHERE TD.TRAN_ID=TM.TRAN_ID
            AND TD.TRAN_TYPE=TM.TRAN_TYPE AND TD.CMP_CODE=TM.CMP_CODE
            AND ISNULL(TD.PARTAMOUNT,0)>0)""").fetchone()[0] or 0)


def get_adv(cur, pid):
    return float(cur.execute(f"SELECT ISNULL(SUM(ISNULL(PARTAMOUNT,0)),0) FROM ADVANCE_ENTRY WHERE LGR_ID={pid} AND CMP_CODE=1").fetchone()[0] or 0)


def main():
    cc = conn(CURR_DB)
    cp = conn(PREV_DB)
    cur_c = cc.cursor()
    cur_p = cp.cursor()

    # Current year
    bills_c  = get_bills(cur_c, PID)
    adj_c    = get_adj(cur_c, PID)
    onacc_dc = get_onacc_d(cur_c, PID)
    onacc_mc = get_onacc_m(cur_c, PID)
    adv_c    = get_adv(cur_c, PID)

    # Previous year
    bills_p  = get_bills(cur_p, PID)
    adj_p    = get_adj(cur_p, PID)
    onacc_dp = get_onacc_d(cur_p, PID)
    onacc_mp = get_onacc_m(cur_p, PID)
    adv_p    = get_adv(cur_p, PID)

    cc.close()
    cp.close()

    total_bills = bills_c + bills_p
    total_adj   = adj_c + adj_p
    total_onacc = onacc_dc + onacc_mc + onacc_dp + onacc_mp
    total_adv   = adv_c + adv_p

    out = total_bills - total_adj - total_onacc - total_adv
    delta = out - TARGET

    print(f"CURR bills={bills_c:,.0f}  adj={adj_c:,.0f}  onaccD={onacc_dc:,.0f}  onaccM={onacc_mc:,.0f}  adv={adv_c:,.0f}")
    print(f"PREV bills={bills_p:,.0f}  adj={adj_p:,.0f}  onaccD={onacc_dp:,.0f}  onaccM={onacc_mp:,.0f}  adv={adv_p:,.0f}")
    print(f"\nTotal bills={total_bills:,.0f}  adj={total_adj:,.0f}  onacc={total_onacc:,.0f}  adv={total_adv:,.0f}")
    print(f"OUTSTANDING = {out:,.0f}  (target={TARGET:,.0f}  delta={delta:,.0f})")
    print("MATCH" if abs(delta) < 5000 else "still off")


if __name__ == "__main__":
    main()
