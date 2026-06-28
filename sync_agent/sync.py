import os
import sys
import csv
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
    """Connect to SQL Server in READ-ONLY mode. Cannot modify/delete/create any data."""
    conn_str = (
        f"DRIVER={{SQL Server}};"
        f"SERVER={SQL_SERVER};"
        f"DATABASE={SQL_DATABASE};"
        f"UID={SQL_USER};"
        f"PWD={SQL_PASSWORD};"
        f"ApplicationIntent=ReadOnly;"
    )
    conn = pyodbc.connect(conn_str, readonly=True)
    # Belt-and-suspenders: explicitly set read-only at connection level
    conn.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
    return conn


def get_admin_token():
    response = requests.post(
        f"{API_URL}/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def date_to_str(val):
    """Convert date/datetime to ISO string (YYYY-MM-DD). Returns None for NULL."""
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val.isoformat()[:10]
    s = str(val).strip()
    if not s or s == "None":
        return None
    return s[:10]


def fetch_orders(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            so.Sal_Order_Id,
            so.Sales_OrderNo,
            so.ConfNo,
            lm.Lgr_name,
            LTRIM(RTRIM(CAST(so.Lgr_Id AS VARCHAR(50)))) AS party_code,
            so.Agent_Id,
            so.Order_Date,
            (SELECT MAX(si.Sal_Inv_Vdate) 
             FROM SALES_INVOICE si 
             WHERE si.ConfNo = so.ConfNo 
               AND si.ConfNo IS NOT NULL 
               AND si.ConfNo != 0
               AND si.Sal_Inv_Vdate >= so.Order_Date
            ) AS Dispatch_Date,
            so.Stop,
            so.FLAG,
            so.Narration1,
            so.TotalQty,
            so.Total_Bales,
            (SELECT ISNULL(SUM(sid.Sal_Inv_Qty), 0)
             FROM SALES_INVOICE si2
             JOIN SALES_INVOICE_DETAIL sid ON si2.Sal_Inv_Id = sid.Sal_Inv_Id
             WHERE si2.ConfNo = so.ConfNo
               AND si2.ConfNo IS NOT NULL
               AND si2.ConfNo != 0
               AND si2.Sal_Inv_Vdate >= so.Order_Date
            ) AS Dispatched_Qty
        FROM SALES_ORDER so
        LEFT JOIN LEDGER_MASTER lm ON so.Lgr_Id = lm.Lgr_Id
        WHERE so.Order_Date >= DATEADD(YEAR, -1, GETDATE())
        ORDER BY so.Order_Date DESC
    """)
    orders = []
    for row in cursor.fetchall():
        # Determine dispatch status using FLAG + actual dispatch quantities
        flag = str(row[9] or "").strip()
        order_qty = float(row[11]) if row[11] else 0
        dispatched_qty = float(row[13]) if row[13] else 0
        dispatch_date = date_to_str(row[7])
        order_date = date_to_str(row[6])

        # Determine status based on actual data
        if row[8]:  # is_stopped
            dispatch_status = "Stopped"
        elif flag.upper() == "C":
            dispatch_status = "Cancelled"
        elif dispatched_qty > 0 and order_qty > 0 and dispatched_qty < order_qty:
            dispatch_status = "Partially Dispatched"
        elif dispatched_qty > 0 and dispatch_date:
            dispatch_status = "Dispatched"
        elif flag.upper() == "S" and dispatch_date:
            dispatch_status = "Dispatched"
        elif flag.upper() == "D":
            dispatch_status = "Delivered"
        elif flag.upper() == "R":
            dispatch_status = "Processing"
        else:
            dispatch_status = "Pending"

        # Use ConfNo as order number if Sales_OrderNo is empty or just "."
        raw_order_no = str(row[1] or "").strip()
        conf_no = row[2]
        if not raw_order_no or raw_order_no in ("", "."):
            order_no = f"ORD-{conf_no}" if conf_no else f"ORD-{row[0]}"
        else:
            order_no = raw_order_no

        orders.append({
            "erp_order_id": row[0],
            "order_no": order_no,
            "conf_no": conf_no,
            "party_name": str(row[3] or "").strip(),
            "party_code": str(row[4] or "").strip(),
            "agent_id": row[5],
            "order_date": order_date,
            "dispatch_date": dispatch_date,
            "is_stopped": bool(row[8]) if row[8] else False,
            "flag": dispatch_status,
            "narration": str(row[10] or "").strip(),
            "total_qty": order_qty,
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
          AND si.ConfNo != 0
    """)
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
            "product_name": str(row[1] or "Unknown Item").strip(),
            "pieces": pcs,
            "quantity": qty or pcs or 1,
            "rate": rate,
            "amount": amount,
            "bill_no": str(row[6] or "").strip(),
        })
    logger.info(f"Fetched invoice items for {len(items)} orders (ConfNos)")
    return items


def fetch_invoices(conn):
    """Fetch invoices for reference data."""
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
            LTRIM(RTRIM(CAST(si.Lgr_Id AS VARCHAR(50)))) AS party_code
        FROM SALES_INVOICE si
        LEFT JOIN LEDGER_MASTER lm ON si.Lgr_Id = lm.Lgr_Id
        WHERE si.Sal_Inv_Vdate >= DATEADD(YEAR, -1, GETDATE())
        ORDER BY si.Sal_Inv_Vdate DESC
    """)
    invoices = []
    for row in cursor.fetchall():
        invoices.append({
            "erp_invoice_id": row[0],
            "bill_no": str(row[1] or "").strip(),
            "invoice_date": date_to_str(row[2]),
            "conf_no": row[3],
            "order_no": str(row[4] or "").strip(),
            "lr_no": str(row[5] or "").strip(),
            "lr_date": date_to_str(row[6]),
            "net_total": float(row[7]) if row[7] else 0,
            "pcs_total": row[8] or 0,
            "bales_total": row[9] or 0,
            "flag": str(row[10] or "").strip(),
            "party_name": str(row[11] or "").strip(),
            "party_code": str(row[12] or "").strip(),
        })
    logger.info(f"Fetched {len(invoices)} invoices")
    return invoices


def fetch_parties(conn):
    """Fetch all parties that have at least one sales order."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT
            lm.Lgr_Id,
            LTRIM(RTRIM(lm.Lgr_name)) AS Lgr_name,
            lm.Lgr_Mobile,
            lm.Lgr_Email,
            lm.Lgr_Add1,
            (SELECT TOP 1 ld.Agent_Id 
             FROM LEDGER_DETAIL ld 
             WHERE ld.Lgr_Id = lm.Lgr_Id AND ld.Agent_Id IS NOT NULL
            ) AS Agent_Id
        FROM LEDGER_MASTER lm
        WHERE lm.Lgr_Id IN (SELECT DISTINCT Lgr_Id FROM SALES_ORDER)
    """)
    parties = []
    for row in cursor.fetchall():
        parties.append({
            "lgr_id": row[0],
            "name": str(row[1] or "").strip(),
            "mobile": str(row[2] or "").strip(),
            "email": str(row[3] or "").strip(),
            "address": str(row[4] or "").strip(),
            "agent_id": row[5],
        })
    logger.info(f"Fetched {len(parties)} parties")
    return parties


def fetch_agents(conn):
    """
    Fetch all agents from ERP.
    Agents are referenced by Agent_Id in SALES_ORDER — their names are in LEDGER_MASTER.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT
            so.Agent_Id,
            lm.Lgr_name,
            lm.Lgr_Mobile,
            lm.Lgr_Email
        FROM SALES_ORDER so
        LEFT JOIN LEDGER_MASTER lm ON so.Agent_Id = lm.Lgr_Id
        WHERE so.Agent_Id IS NOT NULL
          AND so.Agent_Id != 0
          AND so.Order_Date >= DATEADD(YEAR, -1, GETDATE())
    """)
    agents = []
    for row in cursor.fetchall():
        agent_id = row[0]
        if not agent_id:
            continue
        agents.append({
            "agent_id": agent_id,
            "name": str(row[1] or f"Agent {agent_id}").strip(),
            "mobile": str(row[2] or "").strip(),
            "email": str(row[3] or "").strip(),
        })
    logger.info(f"Fetched {len(agents)} agents")
    return agents


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


def auto_create_users(token, parties, agents):
    """
    Create user accounts for ALL new parties and agents.
    
    Party credentials:  username={first_name}{lgr_id}, password=party{lgr_id}
    Agent credentials:  username={first_name}{agent_id}, password=agent{agent_id}
    """
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Get existing users from server
    response = requests.get(f"{API_URL}/admin/users", headers=headers, timeout=30)
    if response.status_code != 200:
        logger.error("Could not fetch existing users, skipping auto-create")
        return

    existing_users = response.json()
    existing_party_codes = {u["party_code"] for u in existing_users if u.get("party_code")}
    existing_agent_codes = {u["agent_code"] for u in existing_users if u.get("agent_code")}

    users_to_create = []

    # --- Party users ---
    new_parties = [p for p in parties if str(p["lgr_id"]) not in existing_party_codes]
    for party in new_parties:
        lgr_id = party["lgr_id"]
        name = party["name"] or f"Party {lgr_id}"
        # Take first word, keep only ASCII alphanumeric, lowercase
        first_word = name.strip().split()[0].lower() if name.strip() else ""
        clean = ''.join(c for c in first_word if c.isascii() and c.isalnum())[:10]
        if not clean:
            clean = "party"

        users_to_create.append({
            "username": f"{clean}{lgr_id}",
            "password": f"party{lgr_id}",
            "role": "party",
            "party_code": str(lgr_id),
            "full_name": name,
        })

    # --- Agent users ---
    new_agents = [a for a in agents if str(a["agent_id"]) not in existing_agent_codes]
    for agent in new_agents:
        agent_id = agent["agent_id"]
        name = agent["name"] or f"Agent {agent_id}"
        first_word = name.strip().split()[0].lower() if name.strip() else ""
        clean = ''.join(c for c in first_word if c.isascii() and c.isalnum())[:10]
        if not clean:
            clean = "agent"

        users_to_create.append({
            "username": f"{clean}{agent_id}",
            "password": f"agent{agent_id}",
            "role": "agent",
            "agent_code": str(agent_id),
            "full_name": name,
        })

    if not users_to_create:
        logger.info("No new parties or agents to create accounts for")
        return

    logger.info(f"Creating accounts for {len(new_parties)} new parties and {len(new_agents)} new agents...")

    response = requests.post(
        f"{API_URL}/admin/users/bulk",
        json={"users": users_to_create},
        headers=headers,
        timeout=600,
    )
    if response.status_code == 200:
        result = response.json()
        logger.info(f"Created {result.get('created', 0)} new accounts (skipped {result.get('skipped', 0)})")
    else:
        logger.error(f"Bulk create failed: {response.text[:200]}")


def export_credentials(token, parties, agents):
    """
    Fetch ALL current users and write credentials.csv (regenerated every sync).
    Passwords follow the known pattern so we can reconstruct them.
    """
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    response = requests.get(f"{API_URL}/admin/users", headers=headers, timeout=30)
    if response.status_code != 200:
        logger.error("Could not fetch users for credential export")
        return

    users = response.json()

    # Build lookup maps
    party_map = {str(p["lgr_id"]): p for p in parties}
    agent_map = {str(a["agent_id"]): a for a in agents}

    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credentials.csv")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Role", "Username", "Password", "Full Name", "Code", "Mobile", "Email"])

        for user in users:
            role = user.get("role", "")
            username = user.get("username", "")
            full_name = user.get("full_name", "")

            if role == "admin":
                continue
            elif role == "party":
                code = user.get("party_code", "")
                password = f"party{code}"
                info = party_map.get(code, {})
                mobile = info.get("mobile", "")
                email = info.get("email", "") or user.get("email", "")
            elif role == "agent":
                code = user.get("agent_code", "")
                password = f"agent{code}"
                info = agent_map.get(code, {})
                mobile = info.get("mobile", "")
                email = info.get("email", "") or user.get("email", "")
            else:
                continue

            writer.writerow([role, username, password, full_name, code, mobile, email])

    user_count = sum(1 for u in users if u.get("role") != "admin")
    logger.info(f"Credential list exported: {csv_path} ({user_count} users)")


def run_sync():
    logger.info("=" * 60)
    logger.info("Starting Baalar sync...")
    start_time = time.time()
    try:
        # Step 1: Connect and fetch from ERP
        logger.info("Connecting to SQL Server...")
        conn = get_db_connection()

        orders = fetch_orders(conn)
        order_items = fetch_order_items(conn)
        invoices = fetch_invoices(conn)
        parties = fetch_parties(conn)
        agents = fetch_agents(conn)
        conn.close()
        logger.info("SQL Server connection closed")

        # Step 2: Authenticate with cloud API
        logger.info("Authenticating with cloud API...")
        token = get_admin_token()

        # Step 3: Filter and prepare data
        items_str_keys = {str(k): v for k, v in order_items.items()}

        # Calculate total_amount per order from invoice items
        # Skip orders with ₹0 total (no invoice = not dispatched yet)
        orders_with_amount = []
        orders_skipped = 0
        for order in orders:
            conf = order["conf_no"]
            if not conf:
                orders_skipped += 1
                continue
            items_for_order = order_items.get(conf, [])
            total = sum(item["amount"] for item in items_for_order)
            if total > 0:
                order["total_amount"] = total
                orders_with_amount.append(order)
            else:
                orders_skipped += 1

        logger.info(
            f"Prepared {len(orders_with_amount)} orders with invoiced items "
            f"(skipped {orders_skipped} with Rs.0 or no ConfNo)"
        )

        # Step 4: Push order data to cloud
        logger.info("Pushing data to cloud...")
        sync_data = {
            "orders": orders_with_amount,
            "order_items": items_str_keys,
            "invoices": invoices,
            "parties": parties,
            "synced_at": datetime.now().isoformat(),
            "total_records": len(orders_with_amount) + len(invoices) + len(parties),
        }
        result = push_to_cloud(token, sync_data)
        logger.info(f"Cloud sync result: {result}")

        # Step 5: Auto-create user accounts for new parties & agents
        logger.info("Checking for new user accounts...")
        auto_create_users(token, parties, agents)

        # Step 6: Export updated credential list
        logger.info("Exporting credential list...")
        export_credentials(token, parties, agents)

        elapsed = time.time() - start_time
        logger.info(f"Sync completed successfully in {elapsed:.1f}s")

    except pyodbc.Error as e:
        logger.error(f"SQL Server error: {e}")
    except requests.exceptions.RequestException as e:
        logger.error(f"API error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)


if __name__ == "__main__":
    run_sync()
