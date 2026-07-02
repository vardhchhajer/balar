"""
Solver #2: Now we know ADJMASTER.AdjustAmt is the cash actually received per bill
and ADJMASTER.Amount is the bill amount being settled. The ERP outstanding must be:
  (Total bills ever issued to party) - (Total cash received) = outstanding.

But "total bills" includes prior years. Let's try:
  Opening_Balance + This_year_Sales - This_year_Cr (ledger) = Cl_Bal (known)
  
The ERP report seems to be bill-reconciliation. Let me try:
  Opening_Balance + SALES_INVOICE_NetTotal - ADJMASTER.AdjustAmt(BR+ADV only)

Also testing whether `Lgr_Op_Bal + sum(ONACCOUNT.PENDING) - sum(ADJMASTER.AdjustAmt)` works.

Known targets:
    20133 = 48,062,253
    25469 =    435,606
    18518 =  5,782,164
"""
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

SQL_SERVER = os.getenv("SQL_SERVER", "INDIASERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE", "Acc2026_2027")
SQL_USER = os.getenv("SQL_USER", "balar_sync")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "")

TARGETS = {20133: 48062253.0, 25469: 435606.0, 18518: 5782164.0}


def conn():
    cs = (
        f"DRIVER={{SQL Server}};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};"
        f"UID={SQL_USER};PWD={SQL_PASSWORD};ApplicationIntent=ReadOnly;"
    )
    c = pyodbc.connect(cs, readonly=True)
    c.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
    return c


def scalar(cur, sql):
    try:
        cur.execute(sql)
        r = cur.fetchone()
        return float(r[0]) if r and r[0] is not None else 0.0
    except Exception as e:
        return f"ERR:{str(e)[:60]}"


def main():
    c = conn()
    cur = c.cursor()

    for pid, target in TARGETS.items():
        print("=" * 60)
        print(f"PARTY {pid}   TARGET = {target:,.0f}")
        print("=" * 60)

        # Components
        op_bal = scalar(cur, f"SELECT ISNULL(Lgr_Op_Bal,0) FROM LEDGER_DETAIL WHERE Lgr_Id={pid} AND Cmp_Code=1")
        si_net = scalar(cur, f"SELECT SUM(ISNULL(Sal_Inv_NetTotal,0)) FROM SALES_INVOICE WHERE Lgr_Id={pid} AND Cmp_Code=1")
        
        # AdjustAmt by type
        adj_br = scalar(cur, f"SELECT SUM(ISNULL(AdjustAmt,0)) FROM ADJMASTER WHERE Lgr_Id={pid} AND Cmp_Code=1 AND Type='BR'")
        adj_all = scalar(cur, f"SELECT SUM(ISNULL(AdjustAmt,0)) FROM ADJMASTER WHERE Lgr_Id={pid} AND Cmp_Code=1")
        amt_all = scalar(cur, f"SELECT SUM(ISNULL(Amount,0)) FROM ADJMASTER WHERE Lgr_Id={pid} AND Cmp_Code=1")
        disc_all = scalar(cur, f"SELECT SUM(ISNULL(Discount,0)+ISNULL(OtherLess,0)) FROM ADJMASTER WHERE Lgr_Id={pid} AND Cmp_Code=1")

        # TRAN_MASTER Cr (all credits posted to this party's ledger)
        tm_cr = scalar(cur, f"""SELECT SUM(ISNULL(Tran_Amount,0)) FROM TRAN_MASTER 
                               WHERE Tran_Master_Id={pid} AND Tran_DrCr='C' AND Cmp_Code=1""")
        # TRAN_DETAIL Cr (detail-side credits)
        td_cr = scalar(cur, f"""SELECT SUM(ISNULL(Tran_Amount,0)) FROM TRAN_DETAIL 
                               WHERE Tran_Detail_Id={pid} AND Tran_DrCr='C' AND Cmp_Code=1""")
        # Total credits from ledger view: master Cr + detail Cr
        total_cr_ledger = scalar(cur, f"SELECT ISNULL(Lgr_Total_Cr_Bal,0) FROM LEDGER_DETAIL WHERE Lgr_Id={pid} AND Cmp_Code=1")
        total_dr_ledger = scalar(cur, f"SELECT ISNULL(Lgr_Total_Dr_Bal,0) FROM LEDGER_DETAIL WHERE Lgr_Id={pid} AND Cmp_Code=1")

        # AUTOJOURNAL credits for this party
        aj_cr = scalar(cur, f"SELECT SUM(ISNULL(CrAmount,0)) FROM AUTOJOURNAL WHERE Lgr_Id={pid} AND Cmp_Code=1")
        aj_dr = scalar(cur, f"SELECT SUM(ISNULL(DrAmount,0)) FROM AUTOJOURNAL WHERE Lgr_Id={pid} AND Cmp_Code=1")

        print(f"  Op_Bal      = {op_bal:,.0f}")
        print(f"  SI_NetTotal = {si_net:,.0f}")
        print(f"  ADJ.AdjustAmt(BR only) = {adj_br:,.0f}")
        print(f"  ADJ.AdjustAmt(all)     = {adj_all:,.0f}")
        print(f"  ADJ.Amount(all)        = {amt_all:,.0f}")
        print(f"  ADJ.Discount+OtherLess = {disc_all:,.0f}")
        print(f"  TRAN_MASTER Cr         = {tm_cr:,.0f}")
        print(f"  TRAN_DETAIL Cr         = {td_cr:,.0f}")
        print(f"  Lgr_Total_Cr_Bal       = {total_cr_ledger:,.0f}")
        print(f"  Lgr_Total_Dr_Bal       = {total_dr_ledger:,.0f}")
        print(f"  AUTOJOURNAL Cr         = {aj_cr:,.0f}")
        print(f"  AUTOJOURNAL Dr         = {aj_dr:,.0f}")

        # CANDIDATE FORMULAS:
        print(f"\n  --- CANDIDATES (target={target:,.0f}) ---")

        # F1: Opening + Sales - AdjustAmt(all)
        f1 = op_bal + si_net - adj_all if all(isinstance(x, float) for x in [op_bal, si_net, adj_all]) else "ERR"
        print(f"  F1: Op + SI - AdjustAmt(all) = {f1:,.0f}" if isinstance(f1, float) else f"  F1: {f1}")

        # F2: Opening + Sales - Amount(all)
        f2 = op_bal + si_net - amt_all if all(isinstance(x, float) for x in [op_bal, si_net, amt_all]) else "ERR"
        print(f"  F2: Op + SI - Amount(all) = {f2:,.0f}" if isinstance(f2, float) else f"  F2: {f2}")

        # F3: Opening + Dr - (Cr + AdjustAmt)
        f3 = op_bal + total_dr_ledger - total_cr_ledger - adj_all if all(isinstance(x, float) for x in [op_bal, total_dr_ledger, total_cr_ledger, adj_all]) else "ERR"
        print(f"  F3: Op + LedgerDr - LedgerCr - AdjustAmt = {f3:,.0f}" if isinstance(f3, float) else f"  F3: {f3}")

        # F4: Opening + Sales - TRAN_DETAIL Cr (which captures ALL receipts into ledger detail)
        f4 = op_bal + si_net - td_cr if all(isinstance(x, float) for x in [op_bal, si_net, td_cr]) else "ERR"
        print(f"  F4: Op + SI - TRAN_DETAIL Cr = {f4:,.0f}" if isinstance(f4, float) else f"  F4: {f4}")

        # F5: Op + Dr_ledger - Cr_ledger (which is just closing bal)
        f5 = op_bal + total_dr_ledger - total_cr_ledger if all(isinstance(x, float) for x in [op_bal, total_dr_ledger, total_cr_ledger]) else "ERR"
        print(f"  F5: Op + LedgerDr - LedgerCr (=ClBal) = {f5:,.0f}" if isinstance(f5, float) else f"  F5: {f5}")

        # F6: Op + SI - (AdjustAmt + Discount)
        f6 = op_bal + si_net - adj_all - disc_all if all(isinstance(x, float) for x in [op_bal, si_net, adj_all, disc_all]) else "ERR"
        print(f"  F6: Op + SI - AdjustAmt - Disc = {f6:,.0f}" if isinstance(f6, float) else f"  F6: {f6}")

        # F7: Op + SI - Amount(all) - Discount
        f7 = op_bal + si_net - amt_all - disc_all if all(isinstance(x, float) for x in [op_bal, si_net, amt_all, disc_all]) else "ERR"
        print(f"  F7: Op + SI - Amount - Disc = {f7:,.0f}" if isinstance(f7, float) else f"  F7: {f7}")

        # F8: Op + SI - adj_br (BR receipts only)
        f8 = op_bal + si_net - adj_br if all(isinstance(x, float) for x in [op_bal, si_net, adj_br]) else "ERR"
        print(f"  F8: Op + SI - AdjustAmt(BR) = {f8:,.0f}" if isinstance(f8, float) else f"  F8: {f8}")

        # F9: Op + SI - Amount(all)  (same as F2)
        # F10: Op + Dr - AdjustAmt (trying different combos)
        f10 = op_bal + total_dr_ledger - adj_all if all(isinstance(x, float) for x in [op_bal, total_dr_ledger, adj_all]) else "ERR"
        print(f"  F10: Op + LedgerDr - AdjustAmt = {f10:,.0f}" if isinstance(f10, float) else f"  F10: {f10}")

        # F11: SI only - adj_br + op_bal - autojournal_cr
        f11 = op_bal + si_net - adj_br - aj_cr if all(isinstance(x, float) for x in [op_bal, si_net, adj_br, aj_cr]) else "ERR"
        print(f"  F11: Op + SI - AdjBR - AutojournalCr = {f11:,.0f}" if isinstance(f11, float) else f"  F11: {f11}")

        # F12: SI - Amount(all) + Op (same as F2 but let's see the delta)
        if isinstance(f2, float):
            print(f"  delta(F2 vs target) = {f2 - target:,.0f}")
        if isinstance(f1, float):
            print(f"  delta(F1 vs target) = {f1 - target:,.0f}")

        print()

    c.close()
    print("DONE")


if __name__ == "__main__":
    main()
