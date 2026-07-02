"""
Bill-wise outstanding verification.

For each party:
  1. Prior-year opening balance (Lgr_Op_Bal)
     minus credits applied to OLD bills (ADJMASTER entries where BillNo NOT in current SALES_INVOICE)
  2. Each current-year bill: Sal_Inv_NetTotal - SUM(ADJMASTER.AdjustAmt for that BillNo)
  
Sum of (1) + all positive (2) should = ERP target.

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


def main():
    c = conn()
    cur = c.cursor()

    for pid, target in TARGETS.items():
        print("=" * 60)
        print(f"PARTY {pid}   TARGET = {target:,.0f}")
        print("=" * 60)

        # Opening balance
        cur.execute(f"SELECT ISNULL(Lgr_Op_Bal,0) FROM LEDGER_DETAIL WHERE Lgr_Id={pid} AND Cmp_Code=1")
        op_bal = float(cur.fetchone()[0] or 0)

        # Total credits applied (from our verified formula)
        cur.execute(f"""
            SELECT
                ISNULL((SELECT SUM(ISNULL(Tran_Amount,0)) FROM TRAN_DETAIL
                        WHERE Tran_Detail_Id={pid} AND Tran_DrCr='C' AND Cmp_Code=1), 0) +
                ISNULL((SELECT SUM(ISNULL(Tran_Amount,0)) FROM TRAN_MASTER
                        WHERE Tran_Master_Id={pid} AND Tran_DrCr='C' AND Cmp_Code=1), 0) +
                ISNULL((SELECT SUM(ISNULL(CrAmount,0)) FROM AUTOJOURNAL
                        WHERE Lgr_Id={pid} AND Cmp_Code=1), 0)
        """)
        total_credits = float(cur.fetchone()[0] or 0)

        # Current year bills
        cur.execute(f"""
            SELECT Sal_Inv_Bill_No, Sal_Inv_NetTotal, Sal_Inv_Vdate
            FROM SALES_INVOICE
            WHERE Lgr_Id={pid} AND Cmp_Code=1
            ORDER BY Sal_Inv_Vdate
        """)
        bills = [(str(r[0]), float(r[1] or 0), r[2]) for r in cur.fetchall()]
        total_billed_this_year = sum(b[1] for b in bills)

        # ADJMASTER adjustments per bill for this party
        cur.execute(f"""
            SELECT BillNo, SUM(ISNULL(AdjustAmt,0)) AS adj
            FROM ADJMASTER
            WHERE Lgr_Id={pid} AND Cmp_Code=1
            GROUP BY BillNo
        """)
        adj_by_bill = {str(r[0]).strip(): float(r[1] or 0) for r in cur.fetchall()}

        # Compute per-bill outstanding
        bill_outstanding_total = 0.0
        unpaid_bills = 0
        partially_paid = 0
        fully_paid = 0
        for bno, amt, dt in bills:
            adj = adj_by_bill.get(bno, 0)
            pending = amt - adj
            if pending > 0.5:
                bill_outstanding_total += pending
                if adj > 0:
                    partially_paid += 1
                else:
                    unpaid_bills += 1
            else:
                fully_paid += 1

        # Credits applied to OLD bills (not matching any current bill)
        current_bill_nos = {str(b[0]) for b in bills}
        adj_to_old_bills = sum(v for k, v in adj_by_bill.items() if k not in current_bill_nos)

        # Prior-year outstanding = Opening - credits applied to old bills
        # But we need to think about this differently:
        # Total outstanding = Op_Bal + SI_Net - All_Credits (our verified formula)
        # Bill-outstanding = sum of (bill_net - bill_adj) for positive bills
        # Prior-year line = Total_outstanding - Bill_outstanding
        
        total_outstanding = op_bal + total_billed_this_year - total_credits
        prior_year_line = total_outstanding - bill_outstanding_total

        print(f"  Opening Balance:     {op_bal:,.0f}")
        print(f"  This-year bills:     {total_billed_this_year:,.0f} ({len(bills)} bills)")
        print(f"  Total credits:       {total_credits:,.0f}")
        print(f"  ADJMASTER to old bills: {adj_to_old_bills:,.0f}")
        print(f"  ---")
        print(f"  Bill-wise outstanding (current yr): {bill_outstanding_total:,.0f}")
        print(f"    - Fully paid bills: {fully_paid}")
        print(f"    - Partially paid:   {partially_paid}")
        print(f"    - Unpaid bills:     {unpaid_bills}")
        print(f"  Prior-year line:     {prior_year_line:,.0f}")
        print(f"  TOTAL (bills + prior): {bill_outstanding_total + prior_year_line:,.0f}")
        print(f"  TARGET:              {target:,.0f}")
        print(f"  DELTA:               {bill_outstanding_total + prior_year_line - target:,.0f}")
        print()

        # Show first 5 unpaid/partially-paid bills as sample
        print(f"  Sample unpaid/partial bills:")
        shown = 0
        for bno, amt, dt in bills:
            adj = adj_by_bill.get(bno, 0)
            pending = amt - adj
            if pending > 0.5 and shown < 5:
                print(f"    Bill#{bno} dt={str(dt)[:10]} billed={amt:,.0f} paid={adj:,.0f} pending={pending:,.0f}")
                shown += 1
        print()

    c.close()
    print("DONE")


if __name__ == "__main__":
    main()
