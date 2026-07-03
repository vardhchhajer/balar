"""
Debug why bills are wrong for MAHALAXMI (5141) and PRAGYA (7370).

For PRAGYA: bills=74,804,884 but check_proc.py gave 75,160,898 (with JOBFLAG='S').
  74,804,884 + 2,000,000 = 76,804,884 (not matching either)
  Actually check_proc.py had bills_S=75,160,898, adj_S=356,014 => net=24,804,884... wait
  check_proc.py had bills=75,160,898, adj=356,014, onacc=50,725,000 => OUT=24,079,884 MATCH
  Now bills=74,804,884 (diff = -356,014 = adj amount), onacc=52,725,000 (diff = +2,000,000)
  
  So two things changed:
  1. bills went DOWN by 356,014 (= adj amount) - when all JOBFLAG included, some bills get adj subtracted
  2. onacc went UP by 2,000,000 - something changed in the on-account filter
  
  => PRAGYA's onacc_d is 52,725,000 vs check_proc.py's 50,725,000. +2,000,000 extra in onacc_d.
  This means a new receipt with PARTAMOUNT=2,000,000 is being picked up now vs before.
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


def conn(db="Acc2026_2027"):
    cs = (f"DRIVER={{SQL Server}};SERVER={SQL_SERVER};DATABASE={db};"
          f"UID={SQL_USER};PWD={SQL_PASSWORD};ApplicationIntent=ReadOnly;")
    c = pyodbc.connect(cs, readonly=True)
    c.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
    return c


def main():
    c = conn()
    cur = c.cursor()

    for pid, label, target in [(7370, "PRAGYA", 24079884.0), (5141, "MAHALAXMI", 244288233.0)]:
        print(f"\n{'='*60}")
        print(f"PARTY {pid} {label}  target={target:,.0f}")

        # check_proc.py used JOBFLAG='S' only and got exact bills
        bills_s = cur.execute(f"SELECT ISNULL(SUM(ISNULL(BILL_AMOUNT,0)),0) FROM PARTYDETAIL WHERE LGR_ID={pid} AND CMP_CODE=1 AND DATE<='{ASON}' AND JOBFLAG='S'").fetchone()[0]
        bills_all = cur.execute(f"SELECT ISNULL(SUM(ISNULL(BILL_AMOUNT,0)),0) FROM PARTYDETAIL WHERE LGR_ID={pid} AND CMP_CODE=1 AND DATE<='{ASON}'").fetchone()[0]
        print(f"PARTYDETAIL BILL_AMOUNT: S-only={float(bills_s or 0):,.0f}  all-flags={float(bills_all or 0):,.0f}")

        # Non-S PARTYDETAIL entries
        print(f"Non-S PARTYDETAIL entries:")
        cur.execute(f"""SELECT JOBFLAG, COUNT(*), SUM(ISNULL(BILL_AMOUNT,0))
                        FROM PARTYDETAIL WHERE LGR_ID={pid} AND CMP_CODE=1 AND DATE<='{ASON}'
                          AND JOBFLAG != 'S'
                        GROUP BY JOBFLAG""")
        for r in cur.fetchall():
            print(f"  {str(r[0]).strip():<6} n={r[1]} bills={float(r[2] or 0):,.0f}")

        # ADJMASTER for non-S bills
        print(f"ADJMASTER for non-S flags:")
        cur.execute(f"""SELECT AM.FLAG, COUNT(*), SUM(ISNULL(AM.ADJUSTAMT,0)), SUM(ISNULL(AM.TOTAL,0))
                        FROM ADJMASTER AM WHERE AM.LGR_ID={pid} AND AM.CMP_CODE=1 AND AM.RECDATE<='{ASON}'
                          AND AM.FLAG != 'S'
                        GROUP BY AM.FLAG""")
        for r in cur.fetchall():
            print(f"  {str(r[0]).strip():<6} n={r[1]} adj={float(r[2] or 0):,.0f} tot={float(r[3] or 0):,.0f}")

        # TRAN_DETAIL PARTAMOUNT change: check_proc.py used types BR/CR/SR/YSR/BP/CP/DN/CN/J
        # check_proc_v3.py uses BR/CR/YSR/BP/CP/DN/CN/J (removed SR)
        # But check_proc.py also had 'SR' in the list. Let me compare:
        onacc_with_sr = float(cur.execute(f"""
            SELECT ISNULL(SUM(ISNULL(TD.PARTAMOUNT,0)),0) FROM TRAN_DETAIL TD
            INNER JOIN TRAN_MASTER TM ON TM.TRAN_ID=TD.TRAN_ID AND TM.TRAN_TYPE=TD.TRAN_TYPE AND TD.CMP_CODE=TM.CMP_CODE
            WHERE TD.Tran_Detail_Id={pid} AND TD.CMP_CODE=1 AND TD.TRAN_DRCR='C'
              AND ISNULL(TD.PARTAMOUNT,0)>0 AND (TD.SHOWPARTAMT=1 OR TD.SHOWPARTAMT IS NULL)
              AND (TD.REC_TRANS=0 OR TD.REC_TRANS IS NULL)
              AND TD.TRAN_TYPE IN ('BR','CR','SR','YSR','BP','CP','DN','CN','J')
        """).fetchone()[0] or 0)

        onacc_without_sr = float(cur.execute(f"""
            SELECT ISNULL(SUM(ISNULL(TD.PARTAMOUNT,0)),0) FROM TRAN_DETAIL TD
            INNER JOIN TRAN_MASTER TM ON TM.TRAN_ID=TD.TRAN_ID AND TM.TRAN_TYPE=TD.TRAN_TYPE AND TD.CMP_CODE=TM.CMP_CODE
            WHERE TD.Tran_Detail_Id={pid} AND TD.CMP_CODE=1 AND TD.TRAN_DRCR='C'
              AND ISNULL(TD.PARTAMOUNT,0)>0 AND (TD.SHOWPARTAMT=1 OR TD.SHOWPARTAMT IS NULL)
              AND (TD.REC_TRANS=0 OR TD.REC_TRANS IS NULL)
              AND TD.TRAN_TYPE IN ('BR','CR','YSR','BP','CP','DN','CN','J')
        """).fetchone()[0] or 0)

        print(f"onacc WITH SR type:    {onacc_with_sr:,.0f}")
        print(f"onacc WITHOUT SR type: {onacc_without_sr:,.0f}")
        print(f"Difference (SR contrib): {onacc_with_sr - onacc_without_sr:,.0f}")

        # Compute with SR included
        adj_s = float(cur.execute(f"SELECT ISNULL(SUM(ISNULL(ADJUSTAMT,0)+ISNULL(TOTAL,0)),0) FROM ADJMASTER WHERE LGR_ID={pid} AND CMP_CODE=1 AND RECDATE<='{ASON}' AND FLAG='S'").fetchone()[0] or 0)
        bills_s_val = float(bills_s or 0)
        out_with_sr = bills_s_val - adj_s - onacc_with_sr
        out_without_sr = bills_s_val - adj_s - onacc_without_sr
        print(f"\nbills_S={bills_s_val:,.0f}  adj_S={adj_s:,.0f}")
        print(f"With SR in onacc:    {out_with_sr:,.0f}  delta={out_with_sr-target:,.0f}")
        print(f"Without SR in onacc: {out_without_sr:,.0f}  delta={out_without_sr-target:,.0f}")

    c.close()
    print("\nDONE")


if __name__ == "__main__":
    main()
