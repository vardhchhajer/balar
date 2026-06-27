import os
import sys
import logging

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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
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


def create_user(token, username, password, role, party_code=None, agent_code=None, full_name=""):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    data = {
        "username": username,
        "password": password,
        "role": role,
        "party_code": party_code,
        "agent_code": agent_code,
        "full_name": full_name,
    }
    response = requests.post(f"{API_URL}/admin/users", json=data, headers=headers, timeout=30)
    if response.status_code == 201:
        logger.info(f"Created {role}: {username} ({full_name})")
        return True
    elif response.status_code == 409:
        logger.info(f"Already exists: {username}")
        return False
    else:
        logger.error(f"Failed {username}: {response.text[:100]}")
        return False


def fetch_parties_from_erp(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT
            lm.Lgr_Id,
            lm.Lgr_name,
            lm.Lgr_Mobile,
            (SELECT TOP 1 ld.Agent_Id FROM LEDGER_DETAIL ld WHERE ld.Lgr_Id = lm.Lgr_Id AND ld.Agent_Id IS NOT NULL) AS Agent_Id
        FROM LEDGER_MASTER lm
        WHERE lm.Lgr_Id IN (SELECT DISTINCT Lgr_Id FROM SALES_ORDER WHERE Order_Date >= DATEADD(YEAR, -1, GETDATE()))
        ORDER BY lm.Lgr_name
    """)
    return cursor.fetchall()


def fetch_agents_from_erp(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT
            ld.Agent_Id,
            agent_lm.Lgr_name AS Agent_Name
        FROM LEDGER_DETAIL ld
        JOIN LEDGER_MASTER agent_lm ON ld.Agent_Id = agent_lm.Lgr_Id
        WHERE ld.Lgr_Id IN (SELECT DISTINCT Lgr_Id FROM SALES_ORDER WHERE Order_Date >= DATEADD(YEAR, -1, GETDATE()))
        AND ld.Agent_Id IS NOT NULL
        ORDER BY agent_lm.Lgr_name
    """)
    return cursor.fetchall()


def make_username(name, lgr_id):
    clean = name.strip().split()[0].lower() if name else "user"
    clean = ''.join(c for c in clean if c.isalnum())[:10]
    return f"{clean}{lgr_id}"


def main():
    logger.info("Connecting to SQL Server...")
    conn = get_db_connection()

    logger.info("Fetching parties and agents from ERP...")
    parties = fetch_parties_from_erp(conn)
    agents = fetch_agents_from_erp(conn)
    conn.close()

    logger.info(f"Found {len(parties)} parties and {len(agents)} agents")

    logger.info("Getting admin token...")
    token = get_admin_token()

    # Create agent users
    logger.info(f"\n--- Creating {len(agents)} agent accounts ---")
    for row in agents:
        agent_id, agent_name = row[0], row[1]
        username = make_username(agent_name, agent_id)
        password = f"agent{agent_id}"
        create_user(token, username, password, "agent", agent_code=str(agent_id), full_name=agent_name or f"Agent {agent_id}")

    # Create party users
    logger.info(f"\n--- Creating {len(parties)} party accounts ---")
    created_file = open("created_users.csv", "w", encoding="utf-8")
    created_file.write("username,password,role,party_code,full_name,mobile\n")

    for row in parties:
        lgr_id, lgr_name, mobile, agent_id = row[0], row[1], row[2], row[3]
        username = make_username(lgr_name, lgr_id)
        password = f"party{lgr_id}"
        success = create_user(token, username, password, "party", party_code=str(lgr_id), full_name=lgr_name or f"Party {lgr_id}")
        created_file.write(f"{username},{password},party,{lgr_id},{lgr_name},{mobile or ''}\n")

    created_file.close()
    logger.info("\nDone! Check 'created_users.csv' for all credentials.")


if __name__ == "__main__":
    main()
