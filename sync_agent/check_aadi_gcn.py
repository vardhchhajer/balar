"""
Final check: AADI's remaining 213,750 gap.
The PROC_OUTSTANDING SQLONACCOUNT7 (prev-year SR/GCN/GDN via TM.TRAN_AMOUNT)
requires TD.PARTAMOUNT > 0. Check which prev-year SR/GCN entries qualify.
"""
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

SQL_SERVER   = os.getenv("SQL_SERVER",   "INDIASERVER")
SQL_USER     = os.getenv("SQL_USER",     "balar_sync")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "")

PID    = 25469
ASON   = "2026-07-03"
TARGET = 435606.0
GAP    = 213750.0


def conn(db):
    cs = (f"DRIVER={{SQL Server}};SERVER={SQL_SERVER};DATABASE={db};"
          f"UID={SQL_USER};PWD={SQL_PASSWORD};ApplicationIntent=ReadOnly;")
    c = pyodbc.connect(cs, readonly=True)
    c.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
    return c


def main():
    cp = conn("Acc2025_2026")
    cur = cp.cursor()

    print(f"=== Prev-year SQLONACCOUNT7: SR/GCN/GDN where TD.PARTAMOUNT > 0 ===")
    print(f"    (uses TM.TRAN_AMOUNT, linked via TM.TRAN_MASTER_ID={PID})")
    cur.execute(f"""
        SELECT TM.TRAN_TYPE, TM.TRAN_AMOUNT, TD.PARTAMOUNT,
               TM.SHOWPARTAMT, TM.REC_TRANS, TM.TRAN_DRCR,
               CONVERT(varchar(10), TM.TRAN_DATE, 120) AS dt
        FROM TRAN_DETAIL TD
        INNER JOIN TRAN_MASTER TM ON TM.TRAN_ID=TD.TRAN_ID
            AND TM.TRAN_TYPE=TD.TRAN_TYPE AND TD.CMP_CODE=TM.CMP_CODE
        WHERE TM.Tran_Master_Id={PID} AND TD.CMP_CODE=1
          AND TD.PARTAMOUNT>0
          AND TM.TRAN_TYPE IN ('SR','GCN','GDN')
          AND TM.TRAN_DRCR='C'
        ORDER BY TM.TRAN_DATE
    """)
    rows = cur.fetchall()
    total_tran = 0.0
    total_part = 0.0
    for r in rows:
        ta = float(r[1] or 0)
        pa = float(r[2] or 0)
        total_tran += ta
        total_part += pa
        print(f"  {str(r[0]).strip():<4} {r[6]} tran_amt={ta:,.0f} part_amt={pa:,.0f} show={r[3]} rec={r[4]} drcr={r[5]}")
    print(f"  SUM TRAN_AMOUNT = {total_tran:,.0f}  (does this = {GAP:,.0f}?)")
    print(f"  SUM PART_AMOUNT = {total_part:,.0f}")

    # Now add to SQLONACCOUNT6 check (current-year)
    cc = conn("Acc2026_2027")
    cur_c = cc.cursor()
    curr_onacc6 = float(cur_c.execute(f"""
        SELECT ISNULL(SUM(
            CASE WHEN TD.TRAN_TYPE='J' THEN
                CASE WHEN TD.TRAN_DRCR='C' THEN TD.PARTAMOUNT ELSE 0 END
            ELSE TM.TRAN_AMOUNT END),0)
        FROM TRAN_DETAIL TD
        INNER JOIN TRAN_MASTER TM ON TM.TRAN_ID=TD.TRAN_ID AND TM.TRAN_TYPE=TD.TRAN_TYPE AND TD.CMP_CODE=TM.CMP_CODE
        WHERE TM.Tran_Master_Id={PID} AND TD.CMP_CODE=1
          AND TD.PARTAMOUNT>0
          AND (TM.SHOWPARTAMT=1 OR TM.SHOWPARTAMT IS NULL)
          AND TM.TRAN_TYPE IN ('SR','GCN','GDN')
          AND (TM.REC_TRANS=0 OR TM.REC_TRANS IS NULL)
          AND TM.TRAN_DRCR='C'
    """).fetchone()[0] or 0)
    print(f"\nCurrent-year SQLONACCOUNT6 for AADI = {curr_onacc6:,.0f}")

    onacc_d = 2094359.0
    bills_adj = 2743715.0
    out = bills_adj - onacc_d - total_tran - curr_onacc6
    print(f"\nbills_adj={bills_adj:,.0f} - onaccD={onacc_d:,.0f} - prev_gcn/sr={total_tran:,.0f} - curr_onacc6={curr_onacc6:,.0f}")
    print(f"  = {out:,.0f}  target={TARGET:,.0f}  delta={out-TARGET:,.0f}")
    print("  MATCH!" if abs(out - TARGET) < 5000 else "  still off")

    cp.close()
    cc.close()
    print("\nDONE")


if __name__ == "__main__":
    main()
