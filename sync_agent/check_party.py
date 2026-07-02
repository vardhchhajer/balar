"""
Identify the exact party for a given Lgr_Id, and list all parties whose
name contains a search term (to disambiguate duplicates like KHUSHBOO).

Run on INDIASERVER:
    cd C:\\Users\\Administrator\\Downloads\\sync_agent\\sync_agent
    py check_party.py
"""
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

SQL_SERVER = os.getenv("SQL_SERVER", "INDIASERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE", "Acc2026_2027")
SQL_USER = os.getenv("SQL_USER", "balar_sync")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "")

TARGET_IDS = [20133, 25469, 18518]
SEARCH = "KHUSHBOO"


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

    print("=== Details for the 3 target party IDs ===")
    for pid in TARGET_IDS:
        try:
            cur.execute(f"""
                SELECT lm.Lgr_Id, lm.Lgr_name, lm.Lgr_Add1, lm.Lgr_Mobile, cm.City_Name
                FROM LEDGER_MASTER lm
                LEFT JOIN CITY_MASTER cm ON lm.City_Id = cm.City_Id
                WHERE lm.Lgr_Id = {pid}
            """)
            r = cur.fetchone()
            if r:
                print(f"  ID {r[0]}: {str(r[1]).strip()} | City={str(r[4] or '').strip()} | Addr={str(r[2] or '').strip()} | Mob={str(r[3] or '').strip()}")
            else:
                print(f"  ID {pid}: NOT FOUND")
        except Exception as e:
            print(f"  ID {pid}: ERR {str(e)[:80]}")

    print(f"\n=== All parties with name containing '{SEARCH}' ===")
    try:
        cur.execute(f"""
            SELECT lm.Lgr_Id, lm.Lgr_name, lm.Lgr_Add1, lm.Lgr_Mobile, cm.City_Name
            FROM LEDGER_MASTER lm
            LEFT JOIN CITY_MASTER cm ON lm.City_Id = cm.City_Id
            WHERE lm.Lgr_name LIKE '%{SEARCH}%'
            ORDER BY lm.Lgr_Id
        """)
        for r in cur.fetchall():
            print(f"  ID {r[0]}: {str(r[1]).strip()} | City={str(r[4] or '').strip()} | Addr={str(r[2] or '').strip()} | Mob={str(r[3] or '').strip()}")
    except Exception as e:
        print(f"  ERR {str(e)[:80]}")

    c.close()
    print("\nDONE")


if __name__ == "__main__":
    main()
