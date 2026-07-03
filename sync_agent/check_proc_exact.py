"""
Exact replication of PROC_OUTSTANDING with @RPT_TYPE=2 (unpaid bills only).

@RPT_TYPE=2 means: exclude bills where ADJMASTER has PAID=1
            i.e. only show bills NOT fully settled.

The procedure computes:
  outstanding = SUM(BILL_AMOUNT - ADJUSTAMT - TOTAL - INTEREST + INTREC)
                for bills WHERE NOT fully paid (PAID!=1 in ADJMASTER)
              + SUM(PARTAMOUNT) from on-account (TRAN_DETAIL, ADVANCE_ENTRY)
              as negative (these reduce the net outstanding)

Actually it returns individual rows and the Crystal Report sums them.
The net is: sum of (BILL_AMOUNT - adj) for unpaid/partial bills
            minus on-account PARTAMOUNT

@RPT_TYPE=2 adds condition:
  (AM.BILLNO+AM.FLAG+VCODE) NOT IN (select ... WHERE PAID=1)
  i.e. exclude bills where there is a PAID=1 ADJMASTER record

Test against all 6 known parties.
"""
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

SQL_SERVER   = os.getenv("SQL_SERVER",   "INDIASERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE", "Acc2026_2027")
SQL_USER     = os.getenv("SQL_USER",     "balar_sync")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "")

ASON = "2026-07-03"  # matches the trace: '03/Jul/2026'
TARGETS = {
    5141: 244288233.0, 20133: 48062253.0, 7370: 24079884.0,
    2879: 7674924.0, 18518: 5782164.0, 25469: 435606.0,
}


def conn():
    cs = (f"DRIVER={{SQL Server}};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};"
          f"UID={SQL_USER};PWD={SQL_PASSWORD};ApplicationIntent=ReadOnly;")
    c = pyodbc.connect(cs, readonly=True)
    c.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
    return c


def one(cur, sql):
    try:
        cur.execute(sql)
        r = cur.fetchone()
        return float(r[0]) if r and r[0] is not None else 0.0
    except Exception as e:
        return f"ERR:{str(e)[:60]}"


def main():
    c = conn()
    cur = c.cursor()
    allok = True

    for pid, target in TARGETS.items():
        # Bills from PARTYDETAIL with ADJMASTER join (RPT_TYPE=2: exclude fully PAID bills)
        # A bill is fully paid when ADJMASTER has PAID=1 for that BILLNO+FLAG+VCODE
        # RPT_TYPE=2 condition: NOT IN (fully paid bills)
        bills_adj = one(cur, f"""
            SELECT SUM(ISNULL(PD.BILL_AMOUNT,0) - ISNULL(AM.ADJUSTAMT,0)
                       - ISNULL(AM.TOTAL,0) - ISNULL(AM.INTEREST,0) + ISNULL(AM.INTREC,0))
            FROM PARTYDETAIL PD
            LEFT JOIN ADJMASTER AM ON AM.BILLNO=PD.BILL_NO AND AM.FLAG=PD.JOBFLAG
                AND AM.CMP_CODE=PD.CMP_CODE AND PD.VCODE=AM.VCODE
                AND AM.RECDATE<='{ASON}'
            WHERE PD.LGR_ID={pid} AND PD.CMP_CODE=1 AND PD.DATE<='{ASON}'
              AND PD.JOBFLAG='S'
              AND (PD.BILL_NO+PD.JOBFLAG+CONVERT(NVARCHAR(50),PD.VCODE)) NOT IN (
                  SELECT AM2.BILLNO+AM2.FLAG+CONVERT(NVARCHAR(50),AM2.VCODE)
                  FROM ADJMASTER AM2
                  WHERE AM2.RECDATE<='{ASON}' AND AM2.PAID=1
                    AND AM2.CMP_CODE=1 AND AM2.LGR_ID={pid}
              )
        """)

        # On-account: TRAN_DETAIL PARTAMOUNT (credit side, unallocated)
        onacc_d = one(cur, f"""
            SELECT ISNULL(SUM(ISNULL(TD.PARTAMOUNT,0)),0)
            FROM TRAN_DETAIL TD
            WHERE TD.Tran_Detail_Id={pid} AND TD.CMP_CODE=1 AND TD.TRAN_DRCR='C'
              AND ISNULL(TD.PARTAMOUNT,0)>0
              AND (TD.SHOWPARTAMT=1 OR TD.SHOWPARTAMT IS NULL)
              AND (TD.REC_TRANS=0 OR TD.REC_TRANS IS NULL)
              AND TD.TRAN_TYPE IN ('BR','CR','YSR','BP','CP','DN','CN','J')
        """)

        # SQLONACCOUNT1: negative debit PARTAMOUNT (payments allocated to JR/DN/BP/CP bills)
        onacc_neg = one(cur, f"""
            SELECT ISNULL(SUM(CASE WHEN TD.TRAN_DRCR='C' THEN 0 ELSE 0-TD.PARTAMOUNT END),0)
            FROM TRAN_DETAIL TD
            INNER JOIN TRAN_MASTER TM ON TM.TRAN_ID=TD.TRAN_ID AND TM.TRAN_TYPE=TD.TRAN_TYPE AND TD.CMP_CODE=TM.CMP_CODE
            WHERE TD.Tran_Detail_Id={pid} AND TD.CMP_CODE=1
              AND (CASE WHEN TD.TRAN_DRCR='C' THEN 0 ELSE 0-TD.PARTAMOUNT END)<>0
              AND (TD.SHOWPARTAMT=1 OR TD.SHOWPARTAMT IS NULL)
              AND TD.TRAN_TYPE IN ('BR','CR','SR','YSR','BP','CP','DN','CN','J')
              AND (TD.REC_TRANS=0 OR TD.REC_TRANS IS NULL)
              AND (CONVERT(NVARCHAR,TM.TRAN_ID)+'JR') NOT IN (
                  SELECT CONVERT(NVARCHAR,VCODE)+JOBFLAG FROM PARTYDETAIL WHERE JOBFLAG='JR')
              AND (CONVERT(NVARCHAR,TM.TRAN_ID)+TM.TRAN_DOCNO+'DN') NOT IN (
                  SELECT CONVERT(NVARCHAR,VCODE)+BILL_NO+JOBFLAG FROM PARTYDETAIL WHERE JOBFLAG='DN')
              AND (CONVERT(NVARCHAR,TM.TRAN_ID)+TM.TRAN_DOCNO+'BP') NOT IN (
                  SELECT CONVERT(NVARCHAR,VCODE)+BILL_NO+JOBFLAG FROM PARTYDETAIL WHERE JOBFLAG='BP')
              AND (CONVERT(NVARCHAR,TM.TRAN_ID)+TM.TRAN_DOCNO+'CP') NOT IN (
                  SELECT CONVERT(NVARCHAR,VCODE)+BILL_NO+JOBFLAG FROM PARTYDETAIL WHERE JOBFLAG='CP')
        """)

        # SQLONACCOUNT6: SR/GCN/GDN master-side with PARTAMOUNT>0 (uses TM.TRAN_AMOUNT)
        onacc_m6 = one(cur, f"""
            SELECT ISNULL(SUM(
                CASE WHEN TD.TRAN_TYPE='J' THEN
                    CASE WHEN TD.TRAN_DRCR='C' THEN TD.PARTAMOUNT ELSE 0 END
                ELSE
                    CASE WHEN TD.TRAN_DRCR='C' THEN TM.TRAN_AMOUNT ELSE TM.TRAN_AMOUNT END
                END),0)
            FROM TRAN_DETAIL TD
            INNER JOIN TRAN_MASTER TM ON TM.TRAN_ID=TD.TRAN_ID AND TM.TRAN_TYPE=TD.TRAN_TYPE AND TD.CMP_CODE=TM.CMP_CODE
            WHERE TM.Tran_Master_Id={pid} AND TD.CMP_CODE=1
              AND TD.PARTAMOUNT>0
              AND (TM.SHOWPARTAMT=1 OR TM.SHOWPARTAMT IS NULL)
              AND TM.TRAN_TYPE IN ('SR','GCN','GDN')
              AND (TM.REC_TRANS=0 OR TM.REC_TRANS IS NULL)
              AND TM.TRAN_DRCR='C'
        """)

        # Advance entries
        adv = one(cur, f"SELECT ISNULL(SUM(ISNULL(PARTAMOUNT,0)),0) FROM ADVANCE_ENTRY WHERE LGR_ID={pid} AND CMP_CODE=1 AND VDATE<='{ASON}'")

        if all(isinstance(x, float) for x in [bills_adj, onacc_d, onacc_neg, onacc_m6, adv]):
            # Net outstanding = bills_adj (already net of adj for unpaid bills) + onacc_neg - onacc_d - onacc_m6 - adv
            out = bills_adj + onacc_neg - onacc_d - onacc_m6 - adv
            d = out - target
            ok = abs(d) < 5000
            allok = allok and ok
            print(f"Party {pid}: bills_adj={bills_adj:,.0f} onaccNeg={onacc_neg:,.0f} onaccD={onacc_d:,.0f} onaccM6={onacc_m6:,.0f} adv={adv:,.0f}")
            print(f"   OUT={out:,.0f} target={target:,.0f} delta={d:,.0f} {'MATCH' if ok else '***OFF***'}")
        else:
            allok = False
            print(f"Party {pid}: ERR bills_adj={bills_adj} onacc_d={onacc_d} onacc_neg={onacc_neg} onacc_m6={onacc_m6}")
        print()

    c.close()
    print("ALL MATCH!" if allok else "some off")


if __name__ == "__main__":
    main()
