# balar

Balar is an automated synchronization and management system that bridges on-premise ERP data with a cloud-based order tracking platform. It enables real-time visibility into sales orders, invoicing, and financial outstanding for business agents and their associated parties.

### Features
*   **ERP Sync Engine:** Automatically extracts sales orders, items, invoices, parties, and agents from SQL Server ERP databases.
*   **Financial Reconciliation:** Implements complex accounting logic (replicating `PROC_OUTSTANDING`) to calculate precise per-party financial outstanding, accounting for adjustments, credits, and advances.
*   **Automated User Provisioning:** Bulk-creates and manages user accounts for parties and agents, with automatic credential generation and export to CSV.
*   **Admin Dashboard API:** Provides administrative endpoints for managing users, monitoring sync status, and forcing manual data refreshes.
*   **Security:** Implements JWT-based authentication, password hashing with `bcrypt`, and account lockout protection for the admin interface.

### Tech Stack
*   **Language:** Python 3.x
*   **API Framework:** FastAPI
*   **Database ORM:** SQLAlchemy (Async)
*   **Database Drivers:** `pyodbc` (SQL Server), `bcrypt`
*   **Networking:** `requests`
*   **Utilities:** `python-dotenv`, `pydantic`, `python-jose`

### Installation

1. Clone the repository and install dependencies:
   ```bash
   pip install fastapi sqlalchemy aiosqlite uvicorn pyodbc requests python-dotenv python-jose[cryptography] bcrypt
   ```

2. Configure environment variables in a `.env` file:
   ```env
   SQL_SERVER=your_server
   SQL_DATABASE=your_db
   SQL_USER=your_user
   SQL_PASSWORD=your_password
   API_URL=https://your-cloud-api.com
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD=your_password
   ```

### Usage

1. **Sync Data:** Run the synchronization agent to pull data from the on-premise ERP and push it to the cloud API:
   ```bash
   python sync_agent/sync.py
   ```

2. **Diagnose Database:** If sync issues occur, run the diagnostic script to verify ERP table schemas and data integrity:
   ```bash
   python sync_agent/diagnose.py > diagnosis.txt
   ```

3. **Admin API:** The FastAPI service manages the incoming data and user authentication. Deploy the application using `uvicorn`:
   ```bash
   uvicorn app.main:app --reload
   ```

### Launch Screen Assets

You can customize the launch screen with your own desired assets by replacing the image files in this directory.

You can also do it by opening your Flutter project's Xcode project with `open ios/Runner.xcworkspace`, selecting `Runner/Assets.xcassets` in the Project Navigator and dropping in the desired images.