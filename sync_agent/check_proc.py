"""
Replicate PROC_OUTSTANDING's logic and test against 6 known ERP figures.

ERP outstanding (receivable) per party, for SUNDRY DEBTORS group:
  bills      = SUM(PARTYDETAIL.BILL_AMOUNT)            [DATE <= ason]
  adjusted   = SUM(ADJMASTER.ADJUSTAMT + TOTAL + INTEREST - INTREC)  [RECDATE <= ason]
  onaccount  = SUM(TRAN_DETAIL.PARTAMOUNT) credits [BR,CR,SR,YSR,BP,CP,DN,CN,J]
  advances   = SUM(ADVANCE_ENTRY.PARTAMOUNT)
  outstanding = bills - adjusted - onaccount - advances

Dumps each component so we can find the exact combination matching the targets.

Targets:
    5141  = 244,288,233
    20133 =  48,062,253
    7370  =  24,079,884
    2879  =   7,674,924
    18518 =   5,782,164
    25469 =     435,606
"""
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

SQL_SERVER = os.getenv("SQL_SERVER", "INDIASERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE", "Acc2026_2027")
SQL_USER = os.getenv("SQL_USER", "balar_sync")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "")

ASON = "2026-07-31"  # captures all current bills/receipts

TARGETS = {
    5141: 244288233.0,
    20133: 48062253.0,
    7370: 24079884.0,
    2879: 7674924.0,
    18518: 5782164.0,
    25469: 435606.0,
}


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
    except Exception as e:
        return f"ERR:{str(e)[:70]}"


def main():
    c = conn()
    cur = c.cursor()

    for pid, target in TARGETS.items():
        print("=" * 60)

        # group name
        grp = "?"
        try:
            cur.execute(f"""SELECT GM.GRP_NAME FROM LEDGER_DETAIL LD
                            JOIN GROUP_MASTER GM ON GM.GRP_ID=LD.GRP_ID
                            WHERE LD.LGR_ID={pid} AND LD.CMP_CODE=1""")
            r = cur.fetchone()
            grp = str(r[0]).strip() if r and r[0] else "(none)"
        except Exception as e:
            grp = f"ERR {str(e)[:40]}"

        bills = one(cur, f"SELECT SUM(ISNULL(BILL_AMOUNT,0)) FROM PARTYDETAIL WHERE LGR_ID={pid} AND CMP_CODE=1 AND DATE<='{ASON}'")
        adj_amt = one(cur, f"SELECT SUM(ISNULL(ADJUSTAMT,0)) FROM ADJMASTER WHERE Lgr_Id={pid} AND CMP_CODE=1 AND RECDATE<='{ASON}'")
        adj_tot = one(cur, f"SELECT SUM(ISNULL(TOTAL,0)) FROM ADJMASTER WHERE Lgr_Id={pid} AND CMP_CODE=1 AND RECDATE<='{ASON}'")
        adj_int = one(cur, f"SELECT SUM(ISNULL(INTEREST,0)) FROM ADJMASTER WHERE Lgr_Id={pid} AND CMP_CODE=1 AND RECDATE<='{ASON}'")
        adj_intrec = one(cur, f"SELECT SUM(ISNULL(INTREC,0)) FROM ADJMASTER WHERE Lgr_Id={pid} AND CMP_CODE=1 AND RECDATE<='{ASON}'")

        onacc = one(cur, f"""SELECT SUM(ISNULL(PARTAMOUNT,0)) FROM TRAN_DETAIL
                             WHERE Tran_Detail_Id={pid} AND CMP_CODE=1 AND TRAN_DRCR='C'
                               AND ISNULL(PARTAMOUNT,0)>0
                               AND (SHOWPARTAMT=1 OR SHOWPARTAMT IS NULL)
                               AND (REC_TRANS=0 OR REC_TRANS IS NULL)
                               AND TRAN_TYPE IN ('BR','CR','SR','YSR','BP','CP','DN','CN','J')""")
        adv = one(cur, f"SELECT SUM(ISNULL(PARTAMOUNT,0)) FROM ADVANCE_ENTRY WHERE LGR_ID={pid} AND CMP_CODE=1 AND VDATE<='{ASON}'")

        print(f"PARTY {pid}   TARGET={target:,.0f}   GROUP={grp}")
        for label, v in [("PARTYDETAIL bills", bills), ("ADJMASTER ADJUSTAMT", adj_amt),
                         ("ADJMASTER TOTAL(disc)", adj_tot), ("ADJMASTER INTEREST", adj_int),
                         ("ADJMASTER INTREC", adj_intrec), ("onaccount PARTAMOUNT", onacc),
                         ("ADVANCE_ENTRY", adv)]:
            print(f"    {label:<24} = {v if isinstance(v,str) else format(v,',.0f')}")

        if all(isinstance(x, float) for x in [bills, adj_amt, adj_tot, adj_int, adj_intrec, onacc, adv]):
            out = bills - adj_amt - adj_tot - adj_int + adj_intrec - onacc - adv
            d = out - target
            print(f"    OUTSTANDING = {out:,.0f}   [delta {d:,.0f}]" + ("  <== MATCH" if abs(d) < 5000 else ""))
            # also without discount/interest
            out2 = bills - adj_amt - onacc - adv
            print(f"    (bills - adjustamt - onacc - adv) = {out2:,.0f}   [delta {out2-target:,.0f}]")
        print()

    c.close()
    print("DONE")


if __name__ == "__main__":
    main()
