"""
SOLVER: The ERP receivable outstanding should subtract only SALES-side credits,
NOT purchase-side credits (FP=Finish Purchase, P, JP, YP, CHP, RP) or payments.

Tests, for all 6 known-answer parties, several credit definitions and shows
which reproduces the ERP figure for ALL of them.

Known ERP targets:
    5141  MAHALAXMI = 244,288,233
    20133 RAM KIRTI =  48,062,253
    7370  PRAGYA    =  24,079,884
    2879  GOVERDHAN =   7,674,924
    18518 KHUSHBOO  =   5,782,164
    25469 AADI TEX  =     435,606
"""
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

SQL_SERVER = os.getenv("SQL_SERVER", "INDIASERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE", "Acc2026_2027")
SQL_USER = os.getenv("SQL_USER", "balar_sync")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "")

TARGETS = {
    5141: 244288233.0,
    20133: 48062253.0,
    7370: 24079884.0,
    2879: 7674924.0,
    18518: 5782164.0,
    25469: 435606.0,
}

# Purchase / payment transaction types that must NOT reduce sales receivable
PURCHASE_TYPES = ['P', 'FP', 'JP', 'YP', 'CHP', 'RP', 'BP', 'CP', 'PR', 'CPR', 'FPR', 'MPR']


def conn():
    cs = (
        f"DRIVER={{SQL Server}};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};"
        f"UID={SQL_USER};PWD={SQL_PASSWORD};ApplicationIntent=ReadOnly;"
    )
    c = pyodbc.connect(cs, readonly=True)
    c.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
    return c


def one(cur, sql):
    try:
        cur.execute(sql)
        r = cur.fetchone()
        return float(r[0]) if r and r[0] is not None else 0.0
    except Exception:
        return 0.0


def main():
    c = conn()
    cur = c.cursor()

    excl = "','".join(PURCHASE_TYPES)
    excl_clause = f"Tran_Type NOT IN ('{excl}')"

    for pid, target in TARGETS.items():
        print("=" * 64)
        op = one(cur, f"SELECT ISNULL(Lgr_Op_Bal,0) FROM LEDGER_DETAIL WHERE Lgr_Id={pid} AND Cmp_Code=1")
        si = one(cur, f"SELECT SUM(ISNULL(Sal_Inv_NetTotal,0)) FROM SALES_INVOICE WHERE Lgr_Id={pid} AND Cmp_Code=1")

        # All credits
        td_all = one(cur, f"SELECT SUM(ISNULL(Tran_Amount,0)) FROM TRAN_DETAIL WHERE Tran_Detail_Id={pid} AND Tran_DrCr='C' AND Cmp_Code=1")
        tm_all = one(cur, f"SELECT SUM(ISNULL(Tran_Amount,0)) FROM TRAN_MASTER WHERE Tran_Master_Id={pid} AND Tran_DrCr='C' AND Cmp_Code=1")
        aj_all = one(cur, f"SELECT SUM(ISNULL(CrAmount,0)) FROM AUTOJOURNAL WHERE Lgr_Id={pid} AND Cmp_Code=1")

        # Credits excluding purchase/payment types
        td_sales = one(cur, f"SELECT SUM(ISNULL(Tran_Amount,0)) FROM TRAN_DETAIL WHERE Tran_Detail_Id={pid} AND Tran_DrCr='C' AND Cmp_Code=1 AND {excl_clause}")
        tm_sales = one(cur, f"SELECT SUM(ISNULL(Tran_Amount,0)) FROM TRAN_MASTER WHERE Tran_Master_Id={pid} AND Tran_DrCr='C' AND Cmp_Code=1 AND {excl_clause}")

        f_all = op + si - td_all - tm_all - aj_all
        f_sales = op + si - td_sales - tm_sales - aj_all

        print(f"PARTY {pid}   TARGET={target:,.0f}")
        print(f"  Opening={op:,.0f}  Sales={si:,.0f}")
        print(f"  Credits ALL:   TD={td_all:,.0f} TM={tm_all:,.0f} AJ={aj_all:,.0f}")
        print(f"  Credits SALES: TD={td_sales:,.0f} TM={tm_sales:,.0f}")
        d_all = f_all - target
        d_sales = f_sales - target
        print(f"  F_all   (subtract all credits)      = {f_all:,.0f}  [delta {d_all:,.0f}]")
        print(f"  F_sales (exclude purchase credits)  = {f_sales:,.0f}  [delta {d_sales:,.0f}]" + ("  <== MATCH" if abs(d_sales) < 5000 else ""))
        print()

    c.close()
    print("DONE")


if __name__ == "__main__":
    main()
