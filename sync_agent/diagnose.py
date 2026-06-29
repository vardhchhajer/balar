"""
Full ERP Database Diagnosis Script
Run on INDIASERVER: py diagnose.py > diagnosis_output.txt
"""
import os
import sys
from datetime import datetime, date
from dotenv import load_dotenv
import pyodbc

load_dotenv()

SQL_SERVER = os.getenv("SQL_SERVER", "INDIASERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE", "Acc2026_2027")
SQL_USER = os.getenv("SQL_USER", "balar_sync")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "")


def connect():
    conn_str = (
        f"DRIVER={{SQL Server}};"
        f"SERVER={SQL_SERVER};"
        f"DATABASE={SQL_DATABASE};"
        f"UID={SQL_USER};"
        f"PWD={SQL_PASSWORD};"
        f"ApplicationIntent=ReadOnly;"
    )
    return pyodbc.connect(conn_str, readonly=True)


def safe_str(val):
    if val is None:
        return "NULL"
    if isinstance(val, (datetime, date)):
        return val.isoformat()[:10]
    return str(val).strip()[:60]


def run_query(cursor, label, sql, max_rows=20):
    print(f"\n{'='*80}")
    print(f"  {label}")
    print(f"{'='*80}")
    try:
        cursor.execute(sql)
        cols = [desc[0] for desc in cursor.description]
        print(f"  Columns: {cols}")
        print(f"  {'-'*70}")
        rows = cursor.fetchmany(max_rows)
        for i, row in enumerate(rows):
            print(f"  [{i}] {[safe_str(v) for v in row]}")
        if not rows:
            print("  (no rows)")
        print(f"  ... Showed {len(rows)} rows")
    except Exception as e:
        print(f"  ERROR: {e}")


def main():
    print("Connecting to SQL Server...")
    conn = connect()
    cursor = conn.cursor()
    print(f"Connected to {SQL_SERVER}/{SQL_DATABASE}")

    # 1. ALL TABLES
    print("\n" + "="*80)
    print("  ALL TABLES IN DATABASE")
    print("="*80)
    cursor.execute("""
        SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_TYPE='BASE TABLE' ORDER BY TABLE_NAME
    """)
    tables = [row[0] for row in cursor.fetchall()]
    for t in tables:
        print(f"  - {t}")
    print(f"  Total: {len(tables)} tables")

    # 2. Schema of key tables
    for table in ["SALES_ORDER", "SALES_INVOICE", "SALES_INVOICE_DETAIL",
                  "LEDGER_MASTER", "LEDGER_DETAIL", "ITEM_MASTER"]:
        print(f"\n{'='*80}")
        print(f"  SCHEMA: {table}")
        print(f"{'='*80}")
        try:
            cursor.execute(f"""
                SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = '{table}'
                ORDER BY ORDINAL_POSITION
            """)
            for row in cursor.fetchall():
                col_name, dtype, max_len, nullable = row
                size = f"({max_len})" if max_len else ""
                print(f"  {col_name:40s} {dtype}{size:10s} {'NULL' if nullable=='YES' else 'NOT NULL'}")
        except Exception as e:
            print(f"  ERROR: {e}")

    # 3. Sample SALES_ORDER
    run_query(cursor, "SALES_ORDER - Recent 20", """
        SELECT TOP 20 
            Sal_Order_Id, Sales_OrderNo, ConfNo, Lgr_Id, Agent_Id, 
            Order_Date, TotalQty, Total_Bales, Stop, FLAG, Narration1
        FROM SALES_ORDER ORDER BY Order_Date DESC
    """)

    # 4. Sample SALES_INVOICE
    run_query(cursor, "SALES_INVOICE - Recent 20", """
        SELECT TOP 20
            Sal_Inv_Id, Sal_Inv_Bill_No, Sal_Inv_Vdate, ConfNo, OrderNo,
            Lgr_Id, Sal_Inv_LrNo, Sal_Inv_LrDate, Sal_Inv_NetTotal,
            Sal_Inv_PcsTotal, Sal_Inv_BalesTotal, Flag
        FROM SALES_INVOICE ORDER BY Sal_Inv_Vdate DESC
    """)

    # 5. Sample SALES_INVOICE_DETAIL
    run_query(cursor, "SALES_INVOICE_DETAIL - 20 rows", """
        SELECT TOP 20
            sid.Sal_Inv_Id, sid.Item_Id, sid.Sal_Inv_Pcs, sid.Sal_Inv_Qty,
            sid.Sal_Inv_Rate, sid.Sal_Inv_Amount, im.Item_Name
        FROM SALES_INVOICE_DETAIL sid
        LEFT JOIN ITEM_MASTER im ON sid.Item_Id = im.Item_Id
    """)

    # 6. ConfNo shared across multiple orders
    run_query(cursor, "ConfNo with MULTIPLE orders (shared ConfNo)", """
        SELECT TOP 20 ConfNo, COUNT(*) AS order_count 
        FROM SALES_ORDER 
        WHERE ConfNo IS NOT NULL AND ConfNo != 0
        GROUP BY ConfNo HAVING COUNT(*) > 1
        ORDER BY COUNT(*) DESC
    """)

    # 7. BUG: dispatch before order (without our fix)
    run_query(cursor, "BUG: MAX invoice date < order date (raw, no filter)", """
        SELECT TOP 30
            so.Sal_Order_Id, so.Sales_OrderNo, so.ConfNo, so.Order_Date,
            (SELECT MAX(si.Sal_Inv_Vdate) FROM SALES_INVOICE si 
             WHERE si.ConfNo = so.ConfNo) AS Max_Inv_Date,
            so.FLAG, so.TotalQty
        FROM SALES_ORDER so
        WHERE so.Order_Date >= DATEADD(YEAR, -1, GETDATE())
          AND so.ConfNo IS NOT NULL AND so.ConfNo != 0
          AND (SELECT MAX(si.Sal_Inv_Vdate) FROM SALES_INVOICE si 
               WHERE si.ConfNo = so.ConfNo) < so.Order_Date
        ORDER BY so.Order_Date DESC
    """)

    # 8. ConfNo reuse across years
    run_query(cursor, "ConfNo REUSE across years (span > 180 days)", """
        SELECT TOP 20 
            ConfNo, MIN(Order_Date) AS earliest, MAX(Order_Date) AS latest,
            COUNT(*) AS order_count,
            DATEDIFF(DAY, MIN(Order_Date), MAX(Order_Date)) AS day_span
        FROM SALES_ORDER
        WHERE ConfNo IS NOT NULL AND ConfNo != 0
        GROUP BY ConfNo
        HAVING DATEDIFF(DAY, MIN(Order_Date), MAX(Order_Date)) > 180
        ORDER BY day_span DESC
    """)

    # 9. FLAG distribution
    run_query(cursor, "SALES_ORDER FLAG distribution (last year)", """
        SELECT FLAG, COUNT(*) AS cnt
        FROM SALES_ORDER
        WHERE Order_Date >= DATEADD(YEAR, -1, GETDATE())
        GROUP BY FLAG ORDER BY cnt DESC
    """)

    # 10. SALES_INVOICE Flag distribution
    run_query(cursor, "SALES_INVOICE Flag distribution (last year)", """
        SELECT Flag, COUNT(*) AS cnt
        FROM SALES_INVOICE
        WHERE Sal_Inv_Vdate >= DATEADD(YEAR, -1, GETDATE())
        GROUP BY Flag ORDER BY cnt DESC
    """)

    # 11. Orders with TotalQty=0 or NULL
    run_query(cursor, "Orders with zero/null TotalQty", """
        SELECT TOP 10
            Sal_Order_Id, Sales_OrderNo, ConfNo, Order_Date, TotalQty, FLAG
        FROM SALES_ORDER
        WHERE Order_Date >= DATEADD(YEAR, -1, GETDATE())
          AND (TotalQty IS NULL OR TotalQty = 0)
        ORDER BY Order_Date DESC
    """)

    # 12. Party mismatch: Invoice Lgr_Id != Order Lgr_Id for same ConfNo
    run_query(cursor, "PARTY MISMATCH: Invoice vs Order party (same ConfNo)", """
        SELECT TOP 20
            so.ConfNo, so.Lgr_Id AS order_party, si.Lgr_Id AS inv_party,
            so.Order_Date, si.Sal_Inv_Vdate
        FROM SALES_ORDER so
        JOIN SALES_INVOICE si ON so.ConfNo = si.ConfNo
        WHERE so.Order_Date >= DATEADD(YEAR, -1, GETDATE())
          AND so.Lgr_Id != si.Lgr_Id
          AND so.ConfNo IS NOT NULL AND so.ConfNo != 0
        ORDER BY so.Order_Date DESC
    """)

    # 13. Partial dispatch check
    run_query(cursor, "DISPATCH QTY comparison: ordered vs invoiced", """
        SELECT TOP 20
            so.Sal_Order_Id, so.ConfNo, so.Order_Date, 
            so.TotalQty AS ordered,
            (SELECT ISNULL(SUM(sid.Sal_Inv_Qty), 0) 
             FROM SALES_INVOICE si2 
             JOIN SALES_INVOICE_DETAIL sid ON si2.Sal_Inv_Id = sid.Sal_Inv_Id
             WHERE si2.ConfNo = so.ConfNo 
               AND si2.Sal_Inv_Vdate >= so.Order_Date
            ) AS dispatched,
            so.FLAG
        FROM SALES_ORDER so
        WHERE so.Order_Date >= DATEADD(YEAR, -1, GETDATE())
          AND so.ConfNo IS NOT NULL AND so.ConfNo != 0
          AND so.TotalQty > 0
        ORDER BY so.Order_Date DESC
    """)

    # 14. LEDGER_DETAIL sample (for agent mapping)
    run_query(cursor, "LEDGER_DETAIL - first 20 rows", """
        SELECT TOP 20 * FROM LEDGER_DETAIL
    """)

    # 15. Orphan invoices (ConfNo not in any order)
    run_query(cursor, "ORPHAN: Invoices with ConfNo not in SALES_ORDER", """
        SELECT TOP 20
            si.Sal_Inv_Id, si.Sal_Inv_Bill_No, si.ConfNo, 
            si.Sal_Inv_Vdate, si.Lgr_Id
        FROM SALES_INVOICE si
        WHERE si.ConfNo IS NOT NULL AND si.ConfNo != 0
          AND si.Sal_Inv_Vdate >= DATEADD(YEAR, -1, GETDATE())
          AND si.ConfNo NOT IN (
              SELECT DISTINCT ConfNo FROM SALES_ORDER WHERE ConfNo IS NOT NULL
          )
    """)

    conn.close()
    print("\n\nDIAGNOSIS COMPLETE.")


if __name__ == "__main__":
    main()
