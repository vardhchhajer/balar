import os
import sys
import time
import logging
from datetime import datetime, date

import pyodbc
import requests
from dotenv import load_dotenv

load_dotenv()

SQL_SERVER = os.getenv("SQL_SERVER", "INDIASERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE", "Acc2026_2027")
SQL_USER = os.getenv("SQL_USER", "balar_sync")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "")
API_URL = os.getenv("API_URL")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("sync.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def get_db_connection():
    conn_str = (
        f"DRIVER={{SQL Server}};"
        f"SERVER={SQL_SERVER};"
        f"DATABASE={SQL_DATABASE};"
        f"UID={SQL_USER};"
        f"PWD={SQL_PASSWORD};"
    )
    return pyodbc.connect(conn_str)


def get_admin_token():
    response = requests.post(
        f"{API_URL}/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def date_to_str(val):
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val.isoformat()[:10]
    return str(val)


def fetch_orders(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            so.Sal_Order_Id,
            so.Sales_OrderNo,
            so.ConfNo,
            lm.Lgr_name,
            CAST(so.Lgr_Id AS VARCHAR),
            so.Agent_Id,
            so.Order_Date,
            (SELECT MAX(si.Sal_Inv_Vdate) FROM SALES_INVOICE si WHERE si.ConfNo = so.ConfNo) AS Dispatch_Date,
            so.Stop,
            so.FLAG,
            so.Narration1,
            so.TotalQty,
            so.Total_Bales
        FROM SALES_ORDER so
        LEFT JOIN LEDGER_MASTER lm ON so.Lgr_Id = lm.Lgr_Id
        WHERE so.Order_Date >= DATEADD(YEAR, -1, GETDATE())
        ORDER BY so.Order_Date DESC
    """)
    orders = []
    for row in cursor.fetchall():
        # Map FLAG to readable status
        flag = row[9] or ""
        flag_map = {
            "S": "Dispatched",
            "D": "Delivered",
            "P": "Pending",
            "C": "Cancelled",
            "R": "Processing",
            "O": "Pending",
        }
        dispatch_status = flag_map.get(flag.upper(), flag if len(flag) > 1 else "Pending")

        # Use ConfNo as order number if Sales_OrderNo is empty or just "."
        raw_order_no = row[1]
        if not raw_order_no or raw_order_no.strip() in ("", "."):
            order_no = f"ORD-{row[2]}"
        else:
            order_no = raw_order_no

        orders.append({
            "erp_order_id": row[0],
            "order_no": order_no,
            "conf_no": row[2],
            "party_name": row[3],
            "party_code": row[4],
            "agent_id": row[5],
            "order_date": date_to_str(row[6]),
            "dispatch_date": date_to_str(row[7]),
            "is_stopped": bool(row[8]) if row[8] else False,
            "flag": dispatch_status,
            "narration": row[10],
            "total_qty": float(row[11]) if row[11] else 0,
            "total_bales": row[12] or 0,
        })
    logger.info(f"Fetched {len(orders)} orders")
    return orders


def fetch_order_items(conn):
    """Fetch items from SALES_INVOICE_DETAIL (has actual dispatched quantities and amounts)."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            si.ConfNo,
            im.Item_Name,
            sid.Sal_Inv_Pcs,
            sid.Sal_Inv_Qty,
            sid.Sal_Inv_Rate,
            sid.Sal_Inv_Amount,
            si.Sal_Inv_Bill_No
        FROM SALES_INVOICE si
        JOIN SALES_INVOICE_DETAIL sid ON si.Sal_Inv_Id = sid.Sal_Inv_Id
        LEFT JOIN ITEM_MASTER im ON sid.Item_Id = im.Item_Id
        WHERE si.Sal_Inv_Vdate >= DATEADD(YEAR, -1, GETDATE())
        AND si.ConfNo IS NOT NULL
    """)
    # Group by ConfNo (which links to SALES_ORDER.ConfNo)
    items = {}
    for row in cursor.fetchall():
        conf_no = row[0]
        if not conf_no:
            continue
        if conf_no not in items:
            items[conf_no] = []
        
        pcs = int(row[2]) if row[2] else 0
        qty = float(row[3]) if row[3] else 0
        rate = float(row[4]) if row[4] else 0
        amount = float(row[5]) if row[5] else 0
        
        # If amount is 0, calculate it
        if not amount:
            amount = (qty or pcs) * rate
        
        items[conf_no].append({
            "product_name": row[1] or "Unknown Item",
            "pieces": pcs,
            "quantity": qty or pcs or 1,
            "rate": rate,
            "amount": amount,
            "bill_no": row[6],
        })
    logger.info(f"Fetched invoice items for {len(items)} orders")
    return items


def fetch_invoices(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            si.Sal_Inv_Id,
            si.Sal_Inv_Bill_No,
            si.Sal_Inv_Vdate,
            si.ConfNo,
            si.OrderNo,
            si.Sal_Inv_LrNo,
            si.Sal_Inv_LrDate,
            si.Sal_Inv_NetTotal,
            si.Sal_Inv_PcsTotal,
            si.Sal_Inv_BalesTotal,
            si.Flag,
            lm.Lgr_name,
            CAST(si.Lgr_Id AS VARCHAR)
        FROM SALES_INVOICE si
        LEFT JOIN LEDGER_MASTER lm ON si.Lgr_Id = lm.Lgr_Id
        WHERE si.Sal_Inv_Vdate >= DATEADD(YEAR, -1, GETDATE())
        ORDER BY si.Sal_Inv_Vdate DESC
    """)
    invoices = []
    for row in cursor.fetchall():
        invoices.append({
            "erp_invoice_id": row[0],
            "bill_no": row[1],
            "invoice_date": date_to_str(row[2]),
            "conf_no": row[3],
            "order_no": row[4],
            "lr_no": row[5],
            "lr_date": date_to_str(row[6]),
            "net_total": float(row[7]) if row[7] else 0,
            "pcs_total": row[8] or 0,
            "bales_total": row[9] or 0,
            "flag": row[10],
            "party_name": row[11],
            "party_code": row[12],
        })
    logger.info(f"Fetched {len(invoices)} invoices")
    return invoices


def fetch_parties(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT
            lm.Lgr_Id,
            lm.Lgr_name,
            lm.Lgr_Mobile,
            lm.Lgr_Email,
            lm.Lgr_Add1,
            (SELECT TOP 1 ld.Agent_Id FROM LEDGER_DETAIL ld WHERE ld.Lgr_Id = lm.Lgr_Id AND ld.Agent_Id IS NOT NULL) AS Agent_Id
        FROM LEDGER_MASTER lm
        WHERE lm.Lgr_Id IN (SELECT DISTINCT Lgr_Id FROM SALES_ORDER)
    """)
    parties = []
    for row in cursor.fetchall():
        parties.append({
            "lgr_id": row[0],
            "name": row[1],
            "mobile": row[2],
            "email": row[3],
            "address": row[4],
            "agent_id": row[5],
        })
    logger.info(f"Fetched {len(parties)} parties")
    return parties


def push_to_cloud(token, data):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    response = requests.post(
        f"{API_URL}/admin/sync/receive",
        json=data,
        headers=headers,
        timeout=300,
    )
    if response.status_code != 200:
        logger.error(f"Server response ({response.status_code}): {response.text[:1000]}")
    response.raise_for_status()
    return response.json()


def run_sync():
    logger.info("=" * 50)
    logger.info("Starting sync...")
    start_time = time.time()
    try:
        logger.info("Connecting to SQL Server...")
        conn = get_db_connection()

        orders = fetch_orders(conn)
        order_items = fetch_order_items(conn)
        invoices = fetch_invoices(conn)
        parties = fetch_parties(conn)
        conn.close()

        logger.info("Authenticating with cloud API...")
        token = get_admin_token()

        logger.info("Pushing data to cloud...")
        # Items are keyed by ConfNo (links orders to invoices)
        items_str_keys = {str(k): v for k, v in order_items.items()}
        
        # Pre-calculate total_amount per order using ConfNo
        for order in orders:
            conf = order["conf_no"]
            items_for_order = order_items.get(conf, [])
            order["total_amount"] = sum(item["amount"] for item in items_for_order)
        
        sync_data = {
            "orders": orders,
            "order_items": items_str_keys,
            "invoices": invoices,
            "parties": parties,
            "synced_at": datetime.now().isoformat(),
            "total_records": len(orders) + len(invoices) + len(parties),
        }
        result = push_to_cloud(token, sync_data)

        elapsed = time.time() - start_time
        logger.info(f"Sync completed in {elapsed:.1f}s - {result}")
    except pyodbc.Error as e:
        logger.error(f"SQL Server error: {e}")
    except requests.exceptions.RequestException as e:
        logger.error(f"API error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    run_sync()
