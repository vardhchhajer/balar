# 🧾 Order Tracker — Complete Full-Stack Build Prompt

> **Instructions:** Paste this entire prompt into an AI coding assistant. Build all files in sequence. Every file must be COMPLETE — no placeholders, no TODOs, no `# implement later`. Generate every line of working code.

---

## 📦 Project Overview

**App Name:** Order Tracker (Flutter project name: `balar`)
**Purpose:** A B2B mobile app where business customers (parties) log in with company-assigned credentials and track their orders (maal) in real-time. Customers can only see orders belonging to their own `party_code`.

**Core User Flow:**
1. Customer logs in with username + password
2. App shows ALL orders belonging to that customer's party
3. Customer taps an order → sees dispatch status, dispatch date, invoice, tracking info
4. Party isolation: users NEVER see another party's orders

**Platform:** Android & iOS (Flutter)
**Version:** 1.0 MVP

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Mobile | Flutter (latest stable), Dart |
| Backend | FastAPI (Python 3.11+) |
| ORM | SQLAlchemy (async) with aiosqlite |
| Database | SQLite for MVP (production: SQL Server) |
| Auth | JWT (access + refresh tokens) |
| State Management | Riverpod (manual providers, NO code generation) |
| HTTP Client | Dio |
| Secure Storage | flutter_secure_storage |
| Navigation | go_router |
| Models | Manual fromJson/toJson (NO freezed, NO code generation) |

> **CRITICAL:** Do NOT use `freezed`, `riverpod_annotation`, or `riverpod_generator`. Write all models manually with `fromJson`/`toJson` factory constructors. Write all Riverpod providers manually. This eliminates `build_runner` complexity entirely.

---

## 🗂 Complete Project Structure

### FastAPI Backend

```
order_tracker_api/
├── main.py
├── requirements.txt
├── .env
├── .env.example
└── app/
    ├── __init__.py
    ├── core/
    │   ├── __init__.py
    │   ├── config.py          # Pydantic settings from .env
    │   ├── security.py        # JWT + bcrypt utilities
    │   ├── database.py        # Async SQLAlchemy engine + session
    │   └── dependencies.py    # get_current_user auth dependency
    ├── models/
    │   ├── __init__.py
    │   ├── user.py            # CustomerUser SQLAlchemy model
    │   └── order.py           # Order SQLAlchemy model
    ├── schemas/
    │   ├── __init__.py
    │   ├── auth.py            # Login/Token Pydantic schemas
    │   ├── order.py           # Order response schemas
    │   └── profile.py         # Profile response schema
    ├── services/
    │   ├── __init__.py
    │   ├── auth_service.py    # Authentication business logic
    │   └── order_service.py   # Order query business logic
    ├── routers/
    │   ├── __init__.py
    │   ├── auth.py            # POST /auth/login, /auth/refresh, /auth/logout
    │   ├── orders.py          # GET /orders, GET /orders/{id}
    │   └── profile.py         # GET /profile
    └── mock/
        ├── __init__.py
        └── seed_data.py       # Seed 2 users + 15 orders
```

### Flutter App

```
balar/
├── pubspec.yaml
└── lib/
    ├── main.dart
    ├── app.dart
    ├── core/
    │   ├── constants/
    │   │   ├── app_colors.dart
    │   │   ├── app_strings.dart
    │   │   └── app_text_styles.dart
    │   ├── errors/
    │   │   ├── app_exception.dart
    │   │   └── failure.dart
    │   ├── network/
    │   │   ├── api_client.dart
    │   │   └── interceptors/
    │   │       ├── auth_interceptor.dart
    │   │       └── error_interceptor.dart
    │   ├── router/
    │   │   └── app_router.dart
    │   ├── storage/
    │   │   └── secure_storage.dart
    │   └── utils/
    │       ├── date_formatter.dart
    │       └── validators.dart
    ├── features/
    │   ├── auth/
    │   │   ├── data/
    │   │   │   ├── models/
    │   │   │   │   └── auth_model.dart
    │   │   │   └── repositories/
    │   │   │       └── auth_repository.dart
    │   │   ├── providers/
    │   │   │   └── auth_provider.dart
    │   │   └── presentation/
    │   │       ├── screens/
    │   │       │   └── login_screen.dart
    │   │       └── widgets/
    │   │           ├── login_form.dart
    │   │           └── logo_header.dart
    │   ├── orders/
    │   │   ├── data/
    │   │   │   ├── models/
    │   │   │   │   └── order_model.dart
    │   │   │   └── repositories/
    │   │   │       └── order_repository.dart
    │   │   ├── providers/
    │   │   │   └── order_provider.dart
    │   │   └── presentation/
    │   │       ├── screens/
    │   │       │   ├── orders_screen.dart
    │   │       │   └── order_detail_screen.dart
    │   │       └── widgets/
    │   │           ├── order_card.dart
    │   │           ├── order_search_bar.dart
    │   │           ├── dispatch_status_badge.dart
    │   │           └── empty_orders_state.dart
    │   └── profile/
    │       ├── data/
    │       │   └── models/
    │       │       └── profile_model.dart
    │       └── presentation/
    │           └── screens/
    │               └── profile_screen.dart
    └── shared/
        └── widgets/
            ├── loading_overlay.dart
            ├── error_widget.dart
            └── app_scaffold.dart
```

---

## 🗃 Database Schema

### Table: `customer_users`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `username` | VARCHAR(100) | Unique, not null |
| `password_hash` | VARCHAR(255) | Bcrypt hashed (cost factor 12) |
| `party_code` | VARCHAR(50) | Links user to their orders |
| `full_name` | VARCHAR(150) | Display name |
| `email` | VARCHAR(200) | Nullable |
| `is_active` | BOOLEAN | Default true |
| `created_at` | DATETIME | Auto timestamp (UTC) |

### Table: `orders`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `party_code` | VARCHAR(50) | Links order to party (NOT a DB FK, just a filter field) |
| `order_no` | VARCHAR(50) | Unique order number (e.g., ORD-2024-001) |
| `order_date` | DATE | When order was placed |
| `dispatch_status` | VARCHAR(50) | Pending, Processing, Dispatched, Delivered, Cancelled |
| `dispatch_date` | DATE | Nullable — set only when dispatched |
| `invoice_no` | VARCHAR(50) | Nullable |
| `tracking_no` | VARCHAR(100) | Nullable |
| `remarks` | TEXT | Nullable |
| `created_at` | DATETIME | Auto timestamp (UTC) |

---

## 🔌 API Contract

### `POST /auth/login`

**Request:**
```json
{ "username": "john_doe", "password": "secret123" }
```
**Response 200:**
```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "token_type": "bearer",
  "expires_in": 3600
}
```
**Error:** `401 { "detail": "Invalid username or password." }`

### `POST /auth/refresh`

**Header:** `Authorization: Bearer <refresh_token>`
**Response 200:**
```json
{ "access_token": "eyJhbGci...", "token_type": "bearer", "expires_in": 3600 }
```

### `POST /auth/logout`

**Header:** `Authorization: Bearer <access_token>`
**Response 200:** `{ "message": "Logged out successfully" }`

### `GET /orders`

**Header:** `Authorization: Bearer <access_token>`
**Query Params:** `search` (optional), `sort_by` (optional: `order_date`|`dispatch_date`, default `order_date`), `sort_order` (optional: `desc`|`asc`, default `desc`)
**Response 200:**
```json
{
  "orders": [
    {
      "id": 1,
      "order_no": "ORD-2024-001",
      "order_date": "2024-10-15",
      "dispatch_status": "Dispatched",
      "dispatch_date": "2024-10-18",
      "invoice_no": "INV-8821",
      "tracking_no": "TRK99201X",
      "remarks": "Fragile items"
    }
  ],
  "total": 12
}
```

### `GET /orders/{order_id}`

**Header:** `Authorization: Bearer <access_token>`
**Response 200:** Single order object (same shape as above).
**Errors:** `404 { "detail": "Order not found." }`, `403 { "detail": "Access denied." }`

### `GET /profile`

**Header:** `Authorization: Bearer <access_token>`
**Response 200:**
```json
{
  "id": 5,
  "username": "john_doe",
  "full_name": "John Doe",
  "email": "john@acmecorp.com",
  "party_code": "ACME001"
}
```

---

## 📱 Screen-by-Screen UI Specification

### 1. Login Screen (`/login`)

**Layout:**
- App logo + "Order Tracker" title centered at ~40% from top
- Card with subtle shadow containing the form
- Username `TextFormField` — person icon prefix, validation: not empty
- Password `TextFormField` — lock icon, visibility toggle, validation: min 6 chars
- "Login" `ElevatedButton` — full width, primary blue color
- "Powered by [Company]" footer text at bottom

**Behavior:**
- Show `CircularProgressIndicator` inside button while loading
- On success → navigate to `/orders`, clear navigation stack
- On error → `SnackBar` with friendly error message
- On app start: check stored tokens → if valid, auto-navigate to `/orders`

---

### 2. Orders List Screen (`/orders`)

**Layout:**
- `AppBar`: "Order Tracker" title, party name subtitle, profile icon (top right → navigates to `/profile`)
- Search bar below AppBar (always visible, filters by order number)
- Order count text: "12 orders found"
- `ListView.builder` wrapped in `RefreshIndicator`
- Each item is an `OrderCard` widget

**OrderCard Layout:**
```
┌─────────────────────────────────────────────────┐
│  ORD-2024-001                  [● Dispatched]   │
│  Order Date: 15 Oct 2024                        │
│  Dispatch Date: 18 Oct 2024                     │
│                                            >    │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  ORD-2024-005              [○ Not Dispatched]   │
│  Order Date: 20 Oct 2024                        │
│  Dispatch Date: —                               │
│                                            >    │
└─────────────────────────────────────────────────┘
```

**Dispatch Status Display Rules:**
| Database Value | Display Label |
|---------------|---------------|
| Pending | Not Dispatched |
| Processing | Not Dispatched |
| Awaiting Dispatch | Not Dispatched |
| Dispatched | Dispatched |
| Delivered | Delivered |
| Cancelled | Cancelled |

**Status Badge Colors:**
| Status | Background | Text Color |
|--------|-----------|------------|
| Not Dispatched | `#FFF3CD` | `#856404` |
| Dispatched | `#D1ECF1` | `#0C5460` |
| Delivered | `#D4EDDA` | `#155724` |
| Cancelled | `#F8D7DA` | `#721C24` |

**Behavior:**
- Auto-loads orders on screen mount
- Pull-to-refresh reloads from API
- Search: debounce 400ms, client-side filter by `order_no`
- Tap card → navigate to `/orders/:id`
- Loading: show 6 shimmer skeleton cards
- Empty: show centered icon + "No orders found" message

---

### 3. Order Detail Screen (`/orders/:id`)

**AppBar:** Back arrow + order number as title

**HERO SECTION — Dispatch Status Banner (most prominent element):**

If dispatched:
```
╔══════════════════════════════════════════════════╗
║  ✅  DISPATCHED                                  ║
║      Dispatch Date: 18 October 2024              ║
╚══════════════════════════════════════════════════╝
```
Background: green `#D4EDDA`, icon: checkmark circle

If not dispatched:
```
╔══════════════════════════════════════════════════╗
║  🕐  NOT YET DISPATCHED                          ║
║      Your order is being processed               ║
╚══════════════════════════════════════════════════╝
```
Background: amber `#FFF3CD`, icon: clock

**Section: Order Information** (Card with rows)

| Label | Value |
|-------|-------|
| Order Number | ORD-2024-001 (bold) |
| Order Date | 15 October 2024 |
| Status | DispatchStatusBadge widget |

**Section: Dispatch Details** (Card with rows, always shown)

| Label | Value |
|-------|-------|
| Dispatch Status | Dispatched / Pending / etc. |
| Dispatch Date | 18 Oct 2024 (or "—") |
| Invoice No. | INV-8821 (or "—") |
| Tracking No. | TRK99201X + copy icon (or "—") |

**Section: Remarks** (only shown if remarks is not null/empty)
- Section heading "Remarks"
- Multi-line text in light gray card

**InfoRow widget:** Label left (14sp, muted, 40% width) | Value right (14sp, bold, 60% width) | Light divider between rows | Null values → "—" (em dash)

---

### 4. Profile Screen (`/profile`)

- Avatar circle with user's initials (large, colored background)
- Full name (large text)
- Username + party code (muted text)
- Email (if available)
- Divider
- "Logout" button — outlined, red/danger color, full width at bottom
- On logout: clear secure storage, navigate to `/login`, clear stack

---

## 🎨 Design Tokens

```dart
class AppColors {
  static const Color primary       = Color(0xFF1A73E8);  // Google Blue
  static const Color primaryDark   = Color(0xFF1557B0);
  static const Color background    = Color(0xFFF5F7FA);
  static const Color surface       = Color(0xFFFFFFFF);
  static const Color textPrimary   = Color(0xFF1A1A2E);
  static const Color textSecondary = Color(0xFF6B7280);
  static const Color border        = Color(0xFFE5E7EB);
  static const Color error         = Color(0xFFDC2626);
  static const Color success       = Color(0xFF16A34A);
  static const Color warning       = Color(0xFFD97706);
}
```

**Typography:** Google Fonts — `Poppins` for headings, `Inter` for body text.

---

## 🔐 Security Requirements

| Requirement | Implementation |
|-------------|---------------|
| Token storage | `flutter_secure_storage` (Keychain on iOS, Keystore on Android) |
| Access token expiry | 1 hour |
| Refresh token expiry | 7 days |
| Auto-refresh | Dio interceptor catches 401, refreshes token, retries original request |
| Party isolation | ALL order DB queries filter by `party_code` from JWT — never trust client-provided party |
| Password hashing | `bcrypt` with cost factor 12 |
| Input validation | Pydantic on backend, form validators on Flutter |
| Error responses | Always `{ "detail": "message" }` — never expose stack traces |

---

## 🌱 Mock Seed Data

Create in `app/mock/seed_data.py` — a runnable script that populates the DB:

**Users (2):**
| username | password | party_code | full_name | email |
|----------|----------|------------|-----------|-------|
| testuser1 | password123 | PARTY001 | Rajesh Kumar | rajesh@acmecorp.com |
| testuser2 | password123 | PARTY002 | Suresh Patel | suresh@betaltd.com |

**Orders (15 total — 10 for PARTY001, 5 for PARTY002):**

| order_no | party_code | order_date | dispatch_status | dispatch_date | invoice_no | tracking_no | remarks |
|----------|-----------|------------|----------------|---------------|------------|-------------|---------|
| ORD-2024-001 | PARTY001 | 2024-10-01 | Dispatched | 2024-10-05 | INV-1001 | TRK10001X | Fragile items |
| ORD-2024-002 | PARTY001 | 2024-10-03 | Dispatched | 2024-10-07 | INV-1002 | TRK10002X | NULL |
| ORD-2024-003 | PARTY001 | 2024-10-08 | Delivered | 2024-10-12 | INV-1003 | TRK10003X | Delivered to warehouse |
| ORD-2024-004 | PARTY001 | 2024-10-10 | Pending | NULL | NULL | NULL | Awaiting stock |
| ORD-2024-005 | PARTY001 | 2024-10-15 | Processing | NULL | NULL | NULL | NULL |
| ORD-2024-006 | PARTY001 | 2024-10-18 | Dispatched | 2024-10-22 | INV-1006 | TRK10006X | Handle with care |
| ORD-2024-007 | PARTY001 | 2024-10-20 | Cancelled | NULL | NULL | NULL | Customer cancelled |
| ORD-2024-008 | PARTY001 | 2024-10-25 | Pending | NULL | NULL | NULL | NULL |
| ORD-2024-009 | PARTY001 | 2024-11-01 | Dispatched | 2024-11-04 | INV-1009 | TRK10009X | NULL |
| ORD-2024-010 | PARTY001 | 2024-11-05 | Delivered | 2024-11-09 | INV-1010 | TRK10010X | Signed by receiver |
| ORD-2024-011 | PARTY002 | 2024-10-05 | Dispatched | 2024-10-09 | INV-2001 | TRK20001X | NULL |
| ORD-2024-012 | PARTY002 | 2024-10-12 | Pending | NULL | NULL | NULL | Waiting for approval |
| ORD-2024-013 | PARTY002 | 2024-10-20 | Dispatched | 2024-10-24 | INV-2003 | TRK20003X | NULL |
| ORD-2024-014 | PARTY002 | 2024-10-28 | Delivered | 2024-11-01 | INV-2004 | TRK20004X | Left at reception |
| ORD-2024-015 | PARTY002 | 2024-11-03 | Processing | NULL | NULL | NULL | NULL |

---

## 📦 Dependencies

### `pubspec.yaml` (Flutter — project name is `balar`)

```yaml
name: balar
description: "Order Tracker - B2B Order Tracking App"
publish_to: 'none'
version: 1.0.0+1

environment:
  sdk: ^3.12.1

dependencies:
  flutter:
    sdk: flutter
  cupertino_icons: ^1.0.8
  flutter_riverpod: ^2.5.1
  go_router: ^13.2.4
  dio: ^5.4.3+1
  flutter_secure_storage: ^9.0.0
  json_annotation: ^4.9.0
  intl: ^0.19.0
  shimmer: ^3.0.0
  google_fonts: ^6.1.0

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^6.0.0

flutter:
  uses-material-design: true
```

> **NO** `freezed`, `freezed_annotation`, `riverpod_annotation`, `riverpod_generator`, `build_runner`, or `json_serializable` in dependencies.

### `requirements.txt` (FastAPI)

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
sqlalchemy[asyncio]==2.0.30
aiosqlite==0.20.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.1
pydantic-settings==2.2.1
pydantic==2.7.1
httpx==0.27.0
python-multipart==0.0.9
```

---

## 🏗 Architecture & Implementation Rules

### Flutter Rules

1. **NO `setState`** for business logic — Riverpod providers only.
2. **NO freezed / NO code generation** — write manual `fromJson`/`toJson` on every model.
3. **NO riverpod_generator** — write `StateNotifierProvider`, `FutureProvider`, etc. manually.
4. Separate `Repository` (HTTP calls via Dio) from `Provider` (state management).
5. All API calls go through `ApiClient` (Dio wrapper). Never call Dio directly from UI.
6. Use `StateNotifier<AsyncValue<T>>` pattern for async state.
7. `flutter_secure_storage` wrapper for reading/writing JWT tokens.
8. All error messages must be user-friendly strings.
9. `go_router` handles ALL navigation. No `Navigator.push` anywhere.
10. `DateFormatter` utility for all date formatting — never format inline in widgets.
11. Use `const` constructors wherever possible.
12. All imports use `package:balar/` (NOT `package:order_tracker/`).

### FastAPI Rules

1. All routes must have `response_model`, `status_code`, and `summary`.
2. Use `Depends(get_current_user)` for all auth-protected routes.
3. JWT verified on every protected route.
4. Error shape: `{ "detail": "error message" }`.
5. Service layer handles business logic — routers only call services.
6. Pydantic v2 models for all request/response schemas.
7. All endpoints appear in Swagger (`/docs`).
8. Passwords hashed with `passlib[bcrypt]` — never stored plain text.
9. Async SQLAlchemy sessions throughout.
10. CORS configured for mobile clients (allow all origins for dev).

---

## 📋 File-by-File Implementation Specifications

### BACKEND FILES

---

#### `order_tracker_api/.env`
```
SECRET_KEY=order-tracker-super-secret-key-change-in-production-2024
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
DATABASE_URL=sqlite+aiosqlite:///./order_tracker.db
```

#### `order_tracker_api/app/core/config.py`
- `class Settings(BaseSettings)` with all env fields
- `model_config` pointing to `.env`
- `@lru_cache def get_settings()` returning singleton

#### `order_tracker_api/app/core/database.py`
- `create_async_engine(DATABASE_URL)`
- `async_sessionmaker` for `AsyncSession`
- `class Base(DeclarativeBase)` — base for all ORM models
- `async def init_db()` — creates all tables
- `async def get_db()` — dependency yielding sessions with commit/rollback

#### `order_tracker_api/app/core/security.py`
- `verify_password(plain, hashed) -> bool` — bcrypt verify
- `get_password_hash(password) -> str` — bcrypt hash
- `create_access_token(data) -> str` — JWT with 1hr expiry, `type: "access"`
- `create_refresh_token(data) -> str` — JWT with 7-day expiry, `type: "refresh"`
- `verify_token(token) -> dict` — decode JWT, raise JWTError on failure

#### `order_tracker_api/app/core/dependencies.py`
- `get_current_user(credentials, db)` — FastAPI dependency
- Uses `HTTPBearer` to extract token from Authorization header
- Decodes JWT, validates `type == "access"`, extracts `sub` (username)
- Queries DB for user, checks `is_active`
- Returns `CustomerUser` model or raises `401`

#### `order_tracker_api/app/models/user.py`
- `class CustomerUser(Base)` — `__tablename__ = "customer_users"`
- All columns from DB schema above

#### `order_tracker_api/app/models/order.py`
- `class Order(Base)` — `__tablename__ = "orders"`
- All columns from DB schema above

#### `order_tracker_api/app/schemas/auth.py`
- `class LoginRequest(BaseModel)`: username: str, password: str
- `class TokenResponse(BaseModel)`: access_token, refresh_token, token_type="bearer", expires_in=3600
- `class RefreshResponse(BaseModel)`: access_token, token_type="bearer", expires_in=3600
- `class MessageResponse(BaseModel)`: message: str

#### `order_tracker_api/app/schemas/order.py`
- `class OrderResponse(BaseModel)`: all order fields, dates as `str | None`, with `model_config = ConfigDict(from_attributes=True)`
- Custom `model_validator` or `field_serializer` to convert `date` objects to ISO strings
- `class OrderListResponse(BaseModel)`: orders: list[OrderResponse], total: int

#### `order_tracker_api/app/schemas/profile.py`
- `class ProfileResponse(BaseModel)`: id, username, full_name, email (optional), party_code

#### `order_tracker_api/app/services/auth_service.py`
- `async def authenticate_user(db, username, password) -> CustomerUser | None`
- `def create_tokens(user) -> TokenResponse` — creates both access and refresh tokens with `sub=username`, `party_code=party_code`
- `def refresh_access_token(refresh_token_str) -> RefreshResponse` — verify refresh token, create new access token

#### `order_tracker_api/app/services/order_service.py`
- `async def get_orders(db, party_code, search, sort_by, sort_order) -> OrderListResponse`
  - ALWAYS filter by `party_code`
  - If `search`: filter `order_no.ilike(f"%{search}%")`
  - Sort by `sort_by` field in `sort_order` direction
- `async def get_order_by_id(db, order_id, party_code) -> Order`
  - Query by `id`, check `party_code` matches → 403 if not, 404 if not found

#### `order_tracker_api/app/routers/auth.py`
- `POST /login` — validate credentials, return tokens
- `POST /refresh` — accept refresh token in Authorization header, return new access token
- `POST /logout` — accept access token, return success message (stateless logout for MVP)

#### `order_tracker_api/app/routers/orders.py`
- `GET /` — list orders with search/sort params, requires `get_current_user`
- `GET /{order_id}` — get single order, requires `get_current_user`, enforces party isolation

#### `order_tracker_api/app/routers/profile.py`
- `GET /` — return current user's profile, requires `get_current_user`

#### `order_tracker_api/app/mock/seed_data.py`
- Runnable script (`if __name__ == "__main__"`)
- Creates tables via `init_db()`
- Checks if data already exists (skip if seeded)
- Inserts 2 users (passwords hashed with bcrypt) and 15 orders from the table above
- Uses `asyncio.run()` to execute

#### `order_tracker_api/main.py`
- Create FastAPI app with `title="Order Tracker API"`, `version="1.0.0"`
- Add CORS middleware (allow all origins for dev)
- Include routers: `auth.router` prefix `/auth`, `orders.router` prefix `/orders`, `profile.router` prefix `/profile`
- `@app.on_event("startup")` — call `init_db()`, then run seed if tables are empty
- `GET /` health check returning `{ "status": "ok", "app": "Order Tracker API" }`

---

### FLUTTER FILES

---

#### `lib/main.dart`
- `WidgetsFlutterBinding.ensureInitialized()`
- `runApp(const ProviderScope(child: OrderTrackerApp()))`

#### `lib/app.dart`
- `OrderTrackerApp` ConsumerWidget
- `MaterialApp.router` with `routerConfig: ref.watch(routerProvider)`
- Theme: `primarySwatch` from AppColors.primary, background, surface, text colors
- Google Fonts: Poppins for headlines, Inter for body
- `debugShowCheckedModeBanner: false`

#### `lib/core/constants/app_colors.dart`
- All colors from design tokens section above
- Additional status colors for badges

#### `lib/core/constants/app_strings.dart`
- `appName = 'Order Tracker'`
- `baseUrl = 'http://10.0.2.2:8000'` (Android emulator → host machine)
- All user-facing strings: login labels, error messages, section headers, etc.

#### `lib/core/constants/app_text_styles.dart`
- `heading1` through `heading3` using GoogleFonts.poppins
- `bodyLarge`, `bodyMedium`, `bodySmall` using GoogleFonts.inter
- `caption`, `button` styles

#### `lib/core/errors/app_exception.dart`
- `class AppException implements Exception` — message + statusCode
- `class UnauthorizedException extends AppException`
- `class NotFoundException extends AppException`
- `class ServerException extends AppException`
- `class NetworkException extends AppException`

#### `lib/core/errors/failure.dart`
- Simple `class Failure` with `final String message`

#### `lib/core/network/api_client.dart`
- `class ApiClient` wrapping Dio instance
- Constructor: sets `baseUrl`, timeouts (30s connect, 30s receive)
- Adds `AuthInterceptor` and `ErrorInterceptor`
- Methods: `Future<Response> get(path, {queryParams})`, `Future<Response> post(path, {data})`
- `apiClientProvider` — Riverpod Provider creating ApiClient instance

#### `lib/core/network/interceptors/auth_interceptor.dart`
- `class AuthInterceptor extends Interceptor`
- `onRequest`: read access token from SecureStorage, add `Authorization: Bearer` header
- `onError`: if 401 → attempt refresh token flow:
  1. Read refresh token from storage
  2. Call `POST /auth/refresh` with refresh token
  3. Save new access token
  4. Retry original request with new token
  5. If refresh also fails → clear all tokens (will trigger redirect to login via auth state)

#### `lib/core/network/interceptors/error_interceptor.dart`
- `class ErrorInterceptor extends Interceptor`
- `onError`: convert `DioException` types to `AppException`:
  - `connectionTimeout`, `receiveTimeout` → `NetworkException`
  - `badResponse` 401 → `UnauthorizedException`
  - `badResponse` 404 → `NotFoundException`
  - `badResponse` other → `ServerException` with detail from response body
  - `connectionError` → `NetworkException`

#### `lib/core/router/app_router.dart`
- `routerProvider` — Provider returning GoRouter
- Routes:
  - `/login` → `LoginScreen`
  - `/orders` → `OrdersScreen`
  - `/orders/:id` → `OrderDetailScreen` (extract `id` from pathParameters)
  - `/profile` → `ProfileScreen`
- `redirect` logic:
  - Read auth state from provider
  - If unauthenticated and not on `/login` → redirect to `/login`
  - If authenticated and on `/login` → redirect to `/orders`
- `refreshListenable` tied to auth state changes

#### `lib/core/storage/secure_storage.dart`
- `class SecureStorage` wrapping `FlutterSecureStorage`
- Constants for keys: `_accessTokenKey`, `_refreshTokenKey`, `_partyCodeKey`, `_fullNameKey`
- Methods: `saveAccessToken`, `getAccessToken`, `saveRefreshToken`, `getRefreshToken`, `saveUserInfo`, `getPartyCode`, `getFullName`, `clearAll`
- `secureStorageProvider` — Riverpod Provider

#### `lib/core/utils/date_formatter.dart`
- `static String formatDate(String? dateStr)` → "15 Oct 2024" or "—"
- `static String formatDateLong(String? dateStr)` → "15 October 2024" or "—"
- Uses `intl` package's `DateFormat`

#### `lib/core/utils/validators.dart`
- `static String? validateUsername(String? value)` — not empty
- `static String? validatePassword(String? value)` — not empty, min 6 chars

---

#### `lib/features/auth/data/models/auth_model.dart`
```dart
class LoginRequest {
  final String username;
  final String password;
  // constructor, toJson()
}

class TokenResponse {
  final String accessToken;
  final String refreshToken;
  final String tokenType;
  final int expiresIn;
  // constructor, factory fromJson(Map<String, dynamic>)
  // Note: JSON keys are snake_case (access_token), Dart fields are camelCase
}
```

#### `lib/features/auth/data/repositories/auth_repository.dart`
- `class AuthRepository` takes `ApiClient` and `SecureStorage`
- `Future<TokenResponse> login(String username, String password)` — POST `/auth/login`, parse response, save tokens + user info to secure storage
- `Future<void> refreshToken()` — POST `/auth/refresh` with stored refresh token
- `Future<void> logout()` — POST `/auth/logout`, clear secure storage
- `authRepositoryProvider` — Riverpod Provider

#### `lib/features/auth/providers/auth_provider.dart`
- `enum AuthStatus { initial, authenticated, unauthenticated, loading }`
- `class AuthState` — status + optional error message
- `class AuthNotifier extends StateNotifier<AuthState>`
  - `checkAuthStatus()` — read tokens from storage, if access token exists → authenticated
  - `login(username, password)` — set loading, call repo, set authenticated or error
  - `logout()` — call repo, set unauthenticated
- `authProvider = StateNotifierProvider<AuthNotifier, AuthState>`

#### `lib/features/auth/presentation/screens/login_screen.dart`
- `ConsumerWidget`
- `Scaffold` with `AppColors.background`
- `SingleChildScrollView` → `Column` with `LogoHeader` + `LoginForm`
- Listen to auth provider for errors → show `SnackBar`

#### `lib/features/auth/presentation/widgets/login_form.dart`
- `ConsumerStatefulWidget` with `TextEditingController`s and `_formKey`
- Card with elevation, rounded corners
- Username field: person icon, validator
- Password field: lock icon, visibility toggle (`_obscurePassword` state), validator
- Login button: full width, primary color, shows `CircularProgressIndicator` when loading
- Calls `ref.read(authProvider.notifier).login(username, password)` on submit

#### `lib/features/auth/presentation/widgets/logo_header.dart`
- Icon (inventory/package icon, size 80, primary color)
- "Order Tracker" text in heading1 style
- "Track your orders in real-time" subtitle in bodyMedium muted style

---

#### `lib/features/orders/data/models/order_model.dart`
```dart
class OrderModel {
  final int id;
  final String orderNo;
  final String orderDate;
  final String dispatchStatus;
  final String? dispatchDate;
  final String? invoiceNo;
  final String? trackingNo;
  final String? remarks;
  // constructor, factory fromJson(Map<String, dynamic>)
  // JSON keys: order_no, order_date, dispatch_status, dispatch_date, invoice_no, tracking_no
}

class OrderListResponse {
  final List<OrderModel> orders;
  final int total;
  // constructor, factory fromJson(Map<String, dynamic>)
}
```

#### `lib/features/orders/data/repositories/order_repository.dart`
- `class OrderRepository` takes `ApiClient`
- `Future<OrderListResponse> getOrders({String? search, String? sortBy, String? sortOrder})` — GET `/orders` with query params
- `Future<OrderModel> getOrderById(int id)` — GET `/orders/$id`
- `orderRepositoryProvider` — Riverpod Provider

#### `lib/features/orders/providers/order_provider.dart`
- `class OrdersNotifier extends StateNotifier<AsyncValue<List<OrderModel>>>`
  - `_allOrders` list (cached for search filtering)
  - `fetchOrders()` — call repo, store in state + cache
  - `searchOrders(String query)` — filter `_allOrders` by `orderNo.contains(query)`
  - `refreshOrders()` — refetch from API
- `ordersProvider = StateNotifierProvider<OrdersNotifier, AsyncValue<List<OrderModel>>>`
- `orderDetailProvider = FutureProvider.family<OrderModel, int>` — fetches single order

#### `lib/features/orders/presentation/screens/orders_screen.dart`
- `ConsumerStatefulWidget`
- `AppBar`: title "Order Tracker", subtitle with party name (from secure storage), profile icon action
- Below AppBar: `OrderSearchBar` widget
- Order count text: "${orders.length} orders found"
- Body: `ref.watch(ordersProvider).when(data: ..., loading: ..., error: ...)`
  - `loading`: 6 shimmer skeleton cards using `shimmer` package
  - `error`: `AppErrorWidget` with retry button
  - `data`: `RefreshIndicator` → `ListView.builder` of `OrderCard` widgets
    - If empty list: `EmptyOrdersState`
- `initState`: trigger `ref.read(ordersProvider.notifier).fetchOrders()`

#### `lib/features/orders/presentation/screens/order_detail_screen.dart`
- `ConsumerWidget`, receives `orderId` from route
- `ref.watch(orderDetailProvider(orderId)).when(...)` 
- **Hero section**: Full-width card at top
  - If `dispatchStatus` is "Dispatched" or "Delivered": green background `#D4EDDA`, checkmark icon, "DISPATCHED", dispatch date formatted long
  - Else: amber background `#FFF3CD`, clock icon, "NOT YET DISPATCHED", "Your order is being processed"
- **Order Information** section: Card with `_InfoRow` widgets for order number, order date, status badge
- **Dispatch Details** section: Card with `_InfoRow` for dispatch status, dispatch date, invoice no, tracking no (with copy-to-clipboard icon button)
- **Remarks** section: Only if `remarks != null && remarks.isNotEmpty`, light gray card with text
- `_InfoRow` widget: Row with label (left, muted, 40%) and value (right, bold, 60%), Divider below

#### `lib/features/orders/presentation/widgets/order_card.dart`
- `Card` with `InkWell` → navigates to `/orders/${order.id}`
- Row 1: Order number (bold, large) + `DispatchStatusBadge` (right-aligned)
- Row 2: "Order Date: ${formatDate(order.orderDate)}" (muted)
- Row 3: "Dispatch Date: ${formatDate(order.dispatchDate)}" or "—" (muted)
- Trailing: chevron right icon
- Subtle elevation, rounded corners

#### `lib/features/orders/presentation/widgets/dispatch_status_badge.dart`
- `class DispatchStatusBadge extends StatelessWidget`
- Takes `String status`
- Displays logic: map raw status to display label:
  - Pending, Processing → "Not Dispatched"
  - Dispatched → "Dispatched"
  - Delivered → "Delivered"
  - Cancelled → "Cancelled"
- Container with rounded corners (pill shape), colored background + colored text per status table above
- Leading dot/icon: ○ (not dispatched), ● (dispatched), ✓ (delivered), ✕ (cancelled)

#### `lib/features/orders/presentation/widgets/order_search_bar.dart`
- `ConsumerStatefulWidget` with `TextEditingController` and `Timer?` for debounce
- `TextField` with search icon prefix, "Search by order number" hint
- Suffix: clear button (X icon) when text is non-empty
- `onChanged`: cancel existing timer, set new 400ms timer, then call `ref.read(ordersProvider.notifier).searchOrders(query)`

#### `lib/features/orders/presentation/widgets/empty_orders_state.dart`
- Centered `Column`: large icon (inbox/package), "No orders found" heading, "Pull down to refresh" subtitle

---

#### `lib/features/profile/data/models/profile_model.dart`
```dart
class ProfileModel {
  final int id;
  final String username;
  final String fullName;
  final String? email;
  final String partyCode;
  // constructor, factory fromJson(Map<String, dynamic>)
}
```

#### `lib/features/profile/presentation/screens/profile_screen.dart`
- `ConsumerWidget`
- Fetches profile from `GET /profile` via a `FutureProvider`
- `CircleAvatar` with initials (first letter of first + last name, or first 2 chars)
- Full name in heading2
- Username in bodyMedium muted
- Party code in bodyMedium muted
- Email in bodyMedium (or "No email on file")
- `Divider`
- Logout button: `OutlinedButton` full width, red border + text, "Logout"
- On tap: confirmation dialog → `ref.read(authProvider.notifier).logout()` → router redirects to `/login`

---

#### `lib/shared/widgets/loading_overlay.dart`
- `Stack` with semi-transparent black overlay + centered `CircularProgressIndicator`
- Takes `bool isLoading` and `Widget child`

#### `lib/shared/widgets/error_widget.dart`
- `AppErrorWidget` — centered column with error icon, message text, "Retry" ElevatedButton
- Takes `String message` and `VoidCallback onRetry`

#### `lib/shared/widgets/app_scaffold.dart`
- Thin wrapper around `Scaffold` with `AppColors.background` as default background
- Takes `appBar`, `body`, optional `floatingActionButton`

---

## 🚀 Quick Start (After All Code Is Generated)

### Backend
```bash
cd order_tracker_api
python -m venv venv
venv\Scripts\activate           # Windows
pip install -r requirements.txt
python app/mock/seed_data.py    # Seed test users + orders
uvicorn main:app --reload --host 0.0.0.0 --port 8000
# Open http://localhost:8000/docs to see Swagger UI
```

**Test credentials:**
- `testuser1` / `password123` (sees 10 orders)
- `testuser2` / `password123` (sees 5 orders)

### Flutter
```bash
cd balar
flutter pub get
# Update lib/core/constants/app_strings.dart baseUrl if needed:
#   Android emulator: http://10.0.2.2:8000
#   iOS simulator: http://localhost:8000
#   Physical device: http://<your-ip>:8000
flutter run
```

---

## ⚠️ Standing Rules (Apply to Every File)

1. **Never skip code.** Every file in the structure must be generated completely.
2. **Never use `# TODO` or `// TODO` or `# implement later`.** All code must be functional.
3. **Use the exact field names** from the DB schema and API contract. Do not rename fields.
4. **Dart null safety** is required — no `!` force-unwrapping without justification.
5. **Python type hints** on every function signature.
6. **All imports must be correct** — verify mentally before writing.
7. **Flutter package name is `balar`** — all imports use `package:balar/...`.
8. **No code generation required** — no `build_runner`, no `freezed`, no `riverpod_generator`.
9. **Dates in API responses are ISO strings** (`"2024-10-15"`) — Flutter parses them as strings and formats for display.
10. **Every file must be listed** with its complete path and every line of code.
