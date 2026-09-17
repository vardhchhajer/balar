# Balar

Balar is an order tracking system for a textile ERP. It combines a Flutter client, a FastAPI service, and a Python sync agent that reads ERP data and sends it to the cloud API. The repository also includes SQL procedures used by the integration.

## Components

- `lib/`: Flutter application for viewing orders and account data.
- `order_tracker_api/`: FastAPI backend and local SQLite database.
- `sync_agent/`: Python agent for reading the ERP database and synchronizing records.
- `test/`: Flutter tests.

## Development setup

1. Install Flutter with Dart 3.5 or newer, Python, and an ODBC driver for the ERP database.
2. In the project root, run `flutter pub get` and `flutter run` for the client.
3. In `order_tracker_api`, create a virtual environment, install `requirements.txt`, and configure environment variables using `.env.example` as a guide. Start the service with `uvicorn main:app --reload`.
4. In `sync_agent`, install `requirements.txt`, configure the ERP connection and API credentials, then run `python sync.py` only against a database you are authorized to access.

The API's interactive documentation is available at `/docs` when it is running. Keep database credentials and API secrets outside version control. Earlier commits included environment files; rotate those credentials before relying on this repository as a public example.
