"""
Diagnose why MAHALAXMI (5141) and PRAGYA (7370) are far too LOW in our formula.
We subtract too much in credits. Break credits down by type to find the
category (purchase, journal, contra, advance) that should NOT count as a
payment against sales outstanding.

Corrections needed (we are too low by):
    5141 MAHALAXMI: 244,288,233 - our  ->  ~29,814,342 over-subtracted
    7370 PRAGYA:     24,079,884 - our  ->  ~11,504,114 over-subtracted
"""
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

SQL_SERVER = os.getenv("SQL_SERVER", "INDIASERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE", "Acc2026_2027")
SQL_USER = os.getenv("SQL_USER", "balar_sync")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "")

TARGETS = {5141: 244288233.0, 7370: 24079884.0, 2879: 7674924.0}


def conn():
    cs = (
        f"DRIVER={{SQL Server}};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};"
        f"UID={SQL_USER};PWD={SQL_PASSWORD};ApplicationIntent=ReadOnly;"
    )
    c = pyodbc.connect(cs, readonly=True)
    c.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
    return c


def rows(cur, sql):
    try:
        cur.execute(sql)
        return cur.fetchall()
    except Exception as e:
        return [("ERR", str(e)[:90])]


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

    for pid, target in TARGETS.items():
        print("=" * 64)
        op = one(cur, f"SELECT ISNULL(Lgr_Op_Bal,0) FROM LEDGER_DETAIL WHERE Lgr_Id={pid} AND Cmp_Code=1")
        opdr = rows(cur, f"SELECT Lgr_Op_DrCr FROM LEDGER_DETAIL WHERE Lgr_Id={pid} AND Cmp_Code=1")
        opdr = str(opdr[0][0]).strip() if opdr and opdr[0][0] else "?"
        si = one(cur, f"SELECT SUM(ISNULL(Sal_Inv_NetTotal,0)) FROM SALES_INVOICE WHERE Lgr_Id={pid} AND Cmp_Code=1")
        td = one(cur, f"SELECT SUM(ISNULL(Tran_Amount,0)) FROM TRAN_DETAIL WHERE Tran_Detail_Id={pid} AND Tran_DrCr='C' AND Cmp_Code=1")
        tm = one(cur, f"SELECT SUM(ISNULL(Tran_Amount,0)) FROM TRAN_MASTER WHERE Tran_Master_Id={pid} AND Tran_DrCr='C' AND Cmp_Code=1")
        aj = one(cur, f"SELECT SUM(ISNULL(CrAmount,0)) FROM AUTOJOURNAL WHERE Lgr_Id={pid} AND Cmp_Code=1")
        our = op + si - td - tm - aj
        print(f"PARTY {pid}   ERP TARGET={target:,.0f}   OUR={our:,.0f}   over-sub={our-target:,.0f}")
        print(f"  Opening={op:,.0f} ({opdr})  Sales={si:,.0f}")
        print(f"  Credits: TD={td:,.0f}  TM={tm:,.0f}  AJ={aj:,.0f}")

        print("  --- TRAN_DETAIL credits by Type ---")
        for r in rows(cur, f"""SELECT Tran_Type, COUNT(*), SUM(ISNULL(Tran_Amount,0))
                               FROM TRAN_DETAIL WHERE Tran_Detail_Id={pid} AND Tran_DrCr='C' AND Cmp_Code=1
                               GROUP BY Tran_Type ORDER BY SUM(ISNULL(Tran_Amount,0)) DESC"""):
            if r[0] == "ERR":
                print(f"    ERR {r[1]}"); break
            print(f"    {str(r[0]).strip():<6} n={r[1]:<5} sum={float(r[2] or 0):,.0f}")

        print("  --- TRAN_DETAIL DEBITS by Type (does party also get debited by non-sales?) ---")
        for r in rows(cur, f"""SELECT Tran_Type, COUNT(*), SUM(ISNULL(Tran_Amount,0))
                               FROM TRAN_DETAIL WHERE Tran_Detail_Id={pid} AND Tran_DrCr='D' AND Cmp_Code=1
                               GROUP BY Tran_Type ORDER BY SUM(ISNULL(Tran_Amount,0)) DESC"""):
            if r[0] == "ERR":
                print(f"    ERR {r[1]}"); break
            print(f"    {str(r[0]).strip():<6} n={r[1]:<5} sum={float(r[2] or 0):,.0f}")

        # Is this party also a supplier? Check purchase invoices
        pur = one(cur, f"SELECT SUM(ISNULL(PurchaseInvNetTotal,0)) FROM PURCHASEINVOICE WHERE Lgr_Id={pid} AND Cmp_Code=1")
        print(f"  Purchase invoices to this party (supplier?): {pur:,.0f}")
        print()

    c.close()
    print("DONE")


if __name__ == "__main__":
    main()
