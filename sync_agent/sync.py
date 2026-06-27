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
            so.vch_Date,
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
        orders.append({
            "erp_order_id": row[0],
            "order_no": row[1] or f"CONF-{row[2]}",
            "conf_no": row[2],
            "party_name": row[3],
            "party_code": row[4],
            "agent_id": row[5],
            "order_date": date_to_str(row[6]),
            "vch_date": date_to_str(row[7]),
            "is_stopped": bool(row[8]) if row[8] else False,
            "flag": row[9],
            "narration": row[10],
            "total_qty": float(row[11]) if row[11] else 0,
            "total_bales": row[12] or 0,
        })
    logger.info(f"Fetched {len(orders)} orders")
    return orders


def fetch_order_items(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            sod.Sal_Order_Id,
            im.Item_Name,
            sod.Bales,
            sod.Pieces,
            sod.Meter,
            sod.Rate,
            sod.PendingBales,
            sod.DeliveredBales,
            sod.Remark
        FROM SALES_ORDER_DETAIL sod
        LEFT JOIN ITEM_MASTER im ON sod.Item_Id = im.Item_Id
        WHERE sod.Sal_Order_Id IN (
            SELECT Sal_Order_Id FROM SALES_ORDER WHERE Order_Date >= DATEADD(YEAR, -1, GETDATE())
        )
    """)
    items = {}
    for row in cursor.fetchall():
        order_id = row[0]
        if order_id not in items:
            items[order_id] = []
        items[order_id].append({
            "product_name": row[1] or "Unknown Item",
            "bales": row[2] or 0,
            "pieces": row[3] or 0,
            "meter": float(row[4]) if row[4] else 0,
            "rate": float(row[5]) if row[5] else 0,
            "pending_bales": row[6] or 0,
            "delivered_bales": row[7] or 0,
            "remark": row[8],
        })
    logger.info(f"Fetched items for {len(items)} orders")
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
        timeout=120,
    )
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
        # Convert order_items keys to strings for JSON
        items_str_keys = {str(k): v for k, v in order_items.items()}
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
