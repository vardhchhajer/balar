"""
Verify FIFO credit allocation reproduces the ERP outstanding exactly and
produces a sensible bill-wise breakdown.

Approach:
  debits = [opening balance (oldest)] + [each current-year bill by date]
  credits = TRAN_DETAIL Cr + TRAN_MASTER Cr + AUTOJOURNAL Cr
  Apply credits oldest-first. Remaining unpaid debits = outstanding.
  Sum of remaining == opening + sales - credits == verified total (guaranteed).

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

        # Total credits (verified formula)
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

        # Current year bills, oldest first
        cur.execute(f"""
            SELECT Sal_Inv_Bill_No, Sal_Inv_NetTotal,
                   CONVERT(varchar(10), Sal_Inv_Vdate, 120) AS bd
            FROM SALES_INVOICE
            WHERE Lgr_Id={pid} AND Cmp_Code=1
            ORDER BY Sal_Inv_Vdate ASC, Sal_Inv_Bill_No ASC
        """)
        bills = [(str(r[0]).strip(), float(r[1] or 0), str(r[2] or "")) for r in cur.fetchall()]

        # Build debit list: opening (oldest) then bills
        debits = []
        if op_bal > 0:
            debits.append({"label": "OPENING", "amount": op_bal, "date": "prior"})
        for bno, amt, bd in bills:
            debits.append({"label": f"Bill#{bno}", "amount": amt, "date": bd})

        # FIFO allocate credits
        remaining_credit = total_credits
        for d in debits:
            if remaining_credit <= 0:
                d["paid"] = 0.0
            elif remaining_credit >= d["amount"]:
                d["paid"] = d["amount"]
                remaining_credit -= d["amount"]
            else:
                d["paid"] = remaining_credit
                remaining_credit = 0.0
            d["pending"] = d["amount"] - d["paid"]

        unpaid = [d for d in debits if d["pending"] > 0.5]
        total_pending = sum(d["pending"] for d in unpaid)

        print(f"  Opening={op_bal:,.0f}  Bills={len(bills)} (sum={sum(b[1] for b in bills):,.0f})  Credits={total_credits:,.0f}")
        print(f"  Verified formula (Op+SI-Cr) = {op_bal + sum(b[1] for b in bills) - total_credits:,.0f}")
        print(f"  FIFO total pending          = {total_pending:,.0f}")
        print(f"  TARGET                      = {target:,.0f}")
        print(f"  DELTA                       = {total_pending - target:,.0f}")
        print(f"  Unpaid debit lines: {len(unpaid)} (opening fully paid: {not any(d['label']=='OPENING' for d in unpaid)})")
        print(f"  First 4 unpaid:")
        for d in unpaid[:4]:
            print(f"    {d['label']} dt={d['date']} amt={d['amount']:,.0f} paid={d['paid']:,.0f} pending={d['pending']:,.0f}")
        print()

    c.close()
    print("DONE")


if __name__ == "__main__":
    main()
