"""
Solver diagnostic: dump every candidate aggregate for the 3 parties whose
true ERP 'TOTAL NET DUE' we now know, so we can find the ONE formula that
reproduces all three targets.

Known ERP targets:
    20133 RAM KIRTI       = 48,062,253
    25469 AADI TEX        =    435,606
    18518 KHUSHBOO FASHION=  5,782,164

Run on INDIASERVER:
    cd C:\\Users\\Administrator\\Downloads\\sync_agent\\sync_agent
    py check_solve.py
Paste the full output back.
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


def rows(cur, sql):
    try:
        cur.execute(sql)
        return cur.fetchall()
    except Exception as e:
        return [("ERR", str(e)[:80])]


def main():
    c = conn()
    cur = c.cursor()

    for pid, target in TARGETS.items():
        print("=" * 60)
        print(f"PARTY {pid}   ERP TARGET = {target:,.0f}")
        print("=" * 60)

        # ONACCOUNT
        oa_p = scalar(cur, f"SELECT SUM(ISNULL(PENDING,0)) FROM ONACCOUNT WHERE PARTY_ID={pid}")
        oa_c = scalar(cur, f"SELECT SUM(ISNULL(PARTCASHAMT,0)) FROM ONACCOUNT WHERE PARTY_ID={pid}")
        oa_a = scalar(cur, f"SELECT SUM(ISNULL(PARTADJAMT,0)) FROM ONACCOUNT WHERE PARTY_ID={pid}")
        print(f"ONACCOUNT: PENDING={oa_p:,.0f} CASH={oa_c:,.0f} ADJ={oa_a:,.0f} net={oa_p-oa_c-oa_a:,.0f}")

        # LEDGER_DETAIL (cmp=1)
        led = rows(cur, f"""SELECT Lgr_Op_Bal, Lgr_Op_DrCr, Lgr_Cl_Bal, Lgr_Cl_DrCr,
                                   Lgr_Total_Dr_Bal, Lgr_Total_Cr_Bal
                            FROM LEDGER_DETAIL WHERE Lgr_Id={pid} AND Cmp_Code=1""")
        print(f"LEDGER_DETAIL(cmp1): {[ (str(x).strip() if x is not None else None) for x in (led[0] if led else []) ]}")

        # ADJMASTER aggregates (cmp=1)
        for col in ["Amount", "AdjustAmt", "Discount", "OtherLess", "Interest", "IntRec", "Total"]:
            v = scalar(cur, f"SELECT SUM(ISNULL({col},0)) FROM ADJMASTER WHERE Lgr_Id={pid} AND Cmp_Code=1")
            print(f"  ADJMASTER.{col} = {v if isinstance(v,str) else format(v, ',.0f')}")

        # ADJMASTER by Type (cmp=1)
        print("  ADJMASTER by Type (Amount):")
        for r in rows(cur, f"""SELECT Type, COUNT(*), SUM(ISNULL(Amount,0)), SUM(ISNULL(AdjustAmt,0))
                               FROM ADJMASTER WHERE Lgr_Id={pid} AND Cmp_Code=1
                               GROUP BY Type ORDER BY Type"""):
            if r[0] == "ERR":
                print(f"    ERR {r[1]}"); break
            print(f"    {str(r[0]).strip():<6} n={r[1]:<4} Amount={float(r[2] or 0):,.0f} AdjustAmt={float(r[3] or 0):,.0f}")

        # SALES_INVOICE totals (this DB, cmp=1)
        si_net = scalar(cur, f"SELECT SUM(ISNULL(Sal_Inv_NetTotal,0)) FROM SALES_INVOICE WHERE Lgr_Id={pid} AND Cmp_Code=1")
        si_cnt = scalar(cur, f"SELECT COUNT(*) FROM SALES_INVOICE WHERE Lgr_Id={pid} AND Cmp_Code=1")
        print(f"SALES_INVOICE(cmp1): NetTotal={si_net if isinstance(si_net,str) else format(si_net,',.0f')} count={si_cnt if isinstance(si_cnt,str) else format(si_cnt,',.0f')}")

        # Candidate: sales bills net - ADJMASTER amount applied
        adj_amt = scalar(cur, f"SELECT SUM(ISNULL(Amount,0)) FROM ADJMASTER WHERE Lgr_Id={pid} AND Cmp_Code=1")
        if isinstance(si_net, float) and isinstance(adj_amt, float):
            print(f"  CANDIDATE si_net - ADJMASTER.Amount = {si_net-adj_amt:,.0f}")
            print(f"  CANDIDATE si_net - ADJMASTER.AdjustAmt = {si_net - scalar(cur, f'SELECT SUM(ISNULL(AdjustAmt,0)) FROM ADJMASTER WHERE Lgr_Id={pid} AND Cmp_Code=1'):,.0f}")

        # Bill-level reconciliation: per sales bill, NetTotal - applied(ADJMASTER by BillNo), floor >0
        billlevel = scalar(cur, f"""
            SELECT SUM(CASE WHEN pend > 0 THEN pend ELSE 0 END) FROM (
                SELECT si.Sal_Inv_Bill_No AS bno,
                       MAX(ISNULL(si.Sal_Inv_NetTotal,0)) -
                       ISNULL((SELECT SUM(ISNULL(am.Amount,0)) FROM ADJMASTER am
                               WHERE am.Lgr_Id=si.Lgr_Id AND am.Cmp_Code=1
                                 AND am.BillNo = CAST(si.Sal_Inv_Bill_No AS NVARCHAR(50))),0) AS pend
                FROM SALES_INVOICE si
                WHERE si.Lgr_Id={pid} AND si.Cmp_Code=1
                GROUP BY si.Sal_Inv_Bill_No, si.Lgr_Id
            ) t
        """)
        print(f"  CANDIDATE bill-level (NetTotal - ADJMASTER.Amount per bill, floor>0) = {billlevel if isinstance(billlevel,str) else format(billlevel,',.0f')}")

        print()

    c.close()
    print("DONE")


if __name__ == "__main__":
    main()
