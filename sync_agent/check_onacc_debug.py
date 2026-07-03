"""
Debug why onacc_d for PRAGYA changed from 50,725,000 to 52,725,000.
The extra 2,000,000 comes from joining TRAN_MASTER for the date filter.

Test: onacc WITH vs WITHOUT the TM join, to isolate the duplication.
"""
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

SQL_SERVER   = os.getenv("SQL_SERVER",   "INDIASERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE", "Acc2026_2027")
SQL_USER     = os.getenv("SQL_USER",     "balar_sync")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "")

ASON = "2026-07-03"
PIDS = [7370, 5141]  # PRAGYA, MAHALAXMI


def conn():
    cs = (f"DRIVER={{SQL Server}};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};"
          f"UID={SQL_USER};PWD={SQL_PASSWORD};ApplicationIntent=ReadOnly;")
    c = pyodbc.connect(cs, readonly=True)
    c.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
    return c


def main():
    c = conn()
    cur = c.cursor()

    for pid in PIDS:
        print(f"\n=== Party {pid} ===")

        # V1: original check_proc.py - no TM join, no date filter on TD
        v1 = float(cur.execute(f"""
            SELECT ISNULL(SUM(ISNULL(PARTAMOUNT,0)),0) FROM TRAN_DETAIL
            WHERE Tran_Detail_Id={pid} AND CMP_CODE=1 AND TRAN_DRCR='C'
              AND ISNULL(PARTAMOUNT,0)>0
              AND (SHOWPARTAMT=1 OR SHOWPARTAMT IS NULL)
              AND (REC_TRANS=0 OR REC_TRANS IS NULL)
              AND TRAN_TYPE IN ('BR','CR','SR','YSR','BP','CP','DN','CN','J')
        """).fetchone()[0] or 0)

        # V2: with INNER JOIN TM for date filter (check_proc_v3.py)
        v2 = float(cur.execute(f"""
            SELECT ISNULL(SUM(ISNULL(TD.PARTAMOUNT,0)),0)
            FROM TRAN_DETAIL TD
            INNER JOIN TRAN_MASTER TM ON TM.TRAN_ID=TD.TRAN_ID
                AND TM.TRAN_TYPE=TD.TRAN_TYPE AND TD.CMP_CODE=TM.CMP_CODE
            WHERE TD.Tran_Detail_Id={pid} AND TD.CMP_CODE=1 AND TD.TRAN_DRCR='C'
              AND ISNULL(TD.PARTAMOUNT,0)>0
              AND (TD.SHOWPARTAMT=1 OR TD.SHOWPARTAMT IS NULL)
              AND (TD.REC_TRANS=0 OR TD.REC_TRANS IS NULL)
              AND TD.TRAN_TYPE IN ('BR','CR','YSR','BP','CP','DN','CN','J')
              AND TM.TRAN_DATE<='{ASON}'
        """).fetchone()[0] or 0)

        print(f"  V1 (no TM join, no date filter): {v1:,.0f}")
        print(f"  V2 (with TM join + date filter):  {v2:,.0f}")
        print(f"  Difference: {v2-v1:,.0f}")

        if abs(v2 - v1) > 0:
            # Find which TM join is causing duplication
            # A TRAN_DETAIL row joins multiple TM rows if there are multiple TM entries for same TRAN_ID+TYPE
            print(f"  Checking for TRAN_DETAIL rows that join multiple TM rows:")
            cur.execute(f"""
                SELECT TOP 5 TD.TRAN_ID, TD.TRAN_TYPE, TD.PARTAMOUNT,
                       COUNT(TM.TRAN_ID) AS tm_count
                FROM TRAN_DETAIL TD
                INNER JOIN TRAN_MASTER TM ON TM.TRAN_ID=TD.TRAN_ID
                    AND TM.TRAN_TYPE=TD.TRAN_TYPE AND TD.CMP_CODE=TM.CMP_CODE
                WHERE TD.Tran_Detail_Id={pid} AND TD.CMP_CODE=1 AND TD.TRAN_DRCR='C'
                  AND ISNULL(TD.PARTAMOUNT,0)>0
                  AND (TD.SHOWPARTAMT=1 OR TD.SHOWPARTAMT IS NULL)
                  AND (TD.REC_TRANS=0 OR TD.REC_TRANS IS NULL)
                  AND TD.TRAN_TYPE IN ('BR','CR','YSR','BP','CP','DN','CN','J')
                  AND TM.TRAN_DATE<='{ASON}'
                GROUP BY TD.TRAN_ID, TD.TRAN_TYPE, TD.PARTAMOUNT
                HAVING COUNT(TM.TRAN_ID) > 1
                ORDER BY TD.PARTAMOUNT DESC
            """)
            for r in cur.fetchall():
                print(f"    TRAN_ID={r[0]} type={r[1]} part={float(r[2] or 0):,.0f} TM_count={r[3]}")

    c.close()
    print("\nDONE")


if __name__ == "__main__":
    main()
