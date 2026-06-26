# Implementation Plan: Order Tracker

## Overview

Build a complete B2B order tracking application with a FastAPI backend and Flutter frontend. The backend provides JWT-authenticated REST APIs with party-isolated order access. The Flutter app uses Riverpod for state management, Dio for networking with automatic token refresh, and go_router for navigation. Implementation proceeds backend-first (core → models → services → routers → seed), then Flutter (core → auth → orders → profile → routing).

## Tasks

- [ ] 1. Backend core setup
  - [ ] 1.1 Create backend project structure and configuration
    - Create `order_tracker_api/` directory with `requirements.txt`, `.env`, `.env.example`
    - Create `order_tracker_api/app/__init__.py` and `order_tracker_api/app/core/__init__.py`
    - Implement `app/core/config.py` with Pydantic Settings loading SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS, DATABASE_URL from `.env`
    - Use `@lru_cache` for `get_settings()` singleton
    - _Requirements: 13.8_

  - [ ] 1.2 Implement database module
    - Create `app/core/database.py` with async SQLAlchemy engine using `aiosqlite`
    - Define `Base` declarative class, `async_sessionmaker`, `init_db()` to create all tables
    - Implement `get_db()` async dependency yielding sessions with commit/rollback
    - _Requirements: 14.1_

  - [ ] 1.3 Implement security utilities
    - Create `app/core/security.py` with bcrypt password hashing (cost factor 12)
    - Implement `verify_password(plain, hashed)`, `get_password_hash(password)`
    - Implement `create_access_token(data)` with 1hr expiry and `type: "access"` claim
    - Implement `create_refresh_token(data)` with 7-day expiry and `type: "refresh"` claim
    - Implement `verify_token(token)` that decodes JWT and raises on failure
    - Include `sub` (username) and `party_code` in JWT payload
    - _Requirements: 1.1, 1.3, 1.4, 2.4_

  - [ ] 1.4 Implement authentication dependency
    - Create `app/core/dependencies.py` with `get_current_user` FastAPI dependency
    - Use `HTTPBearer` to extract token from Authorization header
    - Validate JWT type is "access", extract username, query DB for user
    - Check `is_active` flag, return `CustomerUser` or raise 401
    - Reject if party_code claim is missing or empty
    - _Requirements: 10.1, 10.5, 13.7_

- [ ] 2. Backend models and schemas
  - [ ] 2.1 Create SQLAlchemy models
    - Create `app/models/__init__.py`, `app/models/user.py`, `app/models/order.py`
    - Implement `CustomerUser` model with id, username, password_hash, party_code, full_name, email, is_active, created_at
    - Implement `Order` model with id, party_code, order_no, order_date, dispatch_status, dispatch_date, invoice_no, tracking_no, remarks, created_at
    - _Requirements: 14.2, 14.3_

  - [ ] 2.2 Create Pydantic schemas
    - Create `app/schemas/__init__.py`, `app/schemas/auth.py`, `app/schemas/order.py`, `app/schemas/profile.py`
    - Auth schemas: `LoginRequest`, `TokenResponse`, `RefreshResponse`, `MessageResponse`
    - Order schemas: `OrderResponse` with `model_config = ConfigDict(from_attributes=True)` and date serialization to ISO strings, `OrderListResponse`
    - Profile schema: `ProfileResponse` with id, username, full_name, email (optional), party_code
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_

- [ ] 3. Backend services
  - [ ] 3.1 Implement authentication service
    - Create `app/services/__init__.py` and `app/services/auth_service.py`
    - Implement `authenticate_user(db, username, password)` returning user or None
    - Implement `create_tokens(user)` creating access + refresh tokens with username and party_code claims
    - Implement `refresh_access_token(token)` verifying refresh token type and issuing new access token
    - Implement lockout logic: `check_lockout(db, username)`, `record_failed_attempt(db, username)`, `clear_failed_attempts(db, username)` — 5 consecutive failures locks for 15 minutes
    - _Requirements: 1.1, 1.2, 1.9, 2.4, 2.6_

  - [ ] 3.2 Implement order service
    - Create `app/services/order_service.py`
    - Implement `get_orders(db, party_code, search, sort_by, sort_order)` always filtering by party_code
    - Support search via `order_no.ilike(f"%{search}%")`
    - Validate sort_by (order_date, dispatch_date) and sort_order (asc, desc), reject invalid with 422
    - Apply stable secondary sort by order id descending for deterministic results
    - Implement `get_order_by_id(db, order_id, party_code)` with party isolation (403) and not-found (404)
    - _Requirements: 4.1, 4.2, 5.1, 6.1, 6.2, 6.3, 6.4, 6.5, 7.9, 7.10, 10.1, 10.2, 10.3, 10.4, 10.6_

- [ ] 4. Backend routers and API endpoints
  - [ ] 4.1 Implement auth router
    - Create `app/routers/__init__.py` and `app/routers/auth.py`
    - `POST /login` — validate credentials, check lockout, return tokens or 401
    - `POST /refresh` — accept refresh token via Authorization header, validate type "refresh", return new access token
    - `POST /logout` — accept access token, return success message (stateless for MVP)
    - All endpoints with `response_model`, `status_code`, and `summary`
    - _Requirements: 1.1, 1.2, 1.9, 2.4, 2.6, 3.1, 13.1, 13.2, 13.3_

  - [ ] 4.2 Implement orders router
    - Create `app/routers/orders.py`
    - `GET /` — list orders with optional search, sort_by, sort_order params, requires auth
    - `GET /{order_id}` — single order with party isolation enforcement, requires auth
    - Party_code extracted exclusively from JWT claims, never from request params
    - Error responses: 403 "Access denied.", 404 "Order not found.", 422 for invalid sort params
    - _Requirements: 4.1, 4.2, 4.8, 6.1, 6.2, 6.4, 7.9, 7.10, 10.1, 10.2, 10.4, 13.4, 13.5_

  - [ ] 4.3 Implement profile router
    - Create `app/routers/profile.py`
    - `GET /` — return authenticated user's profile data (id, username, full_name, email, party_code)
    - Requires `get_current_user` dependency
    - _Requirements: 9.3, 13.6_

- [ ] 5. Backend main and seed data
  - [ ] 5.1 Implement seed data module
    - Create `app/mock/__init__.py` and `app/mock/seed_data.py`
    - Seed 2 users: testuser1 (PARTY001, "Rajesh Kumar") and testuser2 (PARTY002, "Suresh Patel") with bcrypt-hashed passwords
    - Seed 15 orders: 10 for PARTY001, 5 for PARTY002 with varied dispatch statuses
    - Check if data exists before seeding (idempotent)
    - Include all order fields from the mock data table in requirements
    - _Requirements: 14.1, 14.2, 14.3, 14.4_

  - [ ] 5.2 Implement main application entry point
    - Create `order_tracker_api/main.py` with FastAPI app (title, version)
    - Add CORS middleware allowing all origins for development
    - Include auth, orders, profile routers with proper prefixes
    - Startup event: call `init_db()`, run seed if tables are empty
    - Health check endpoint `GET /` returning `{"status": "ok", "app": "Order Tracker API"}`
    - _Requirements: 13.8, 14.1, 14.4_

- [ ] 6. Checkpoint - Verify backend runs
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Flutter core setup
  - [ ] 7.1 Create Flutter constants and theme
    - Create `lib/core/constants/app_colors.dart` with all design tokens (primary, background, surface, text, status badge colors)
    - Create `lib/core/constants/app_strings.dart` with app name, base URL (`http://10.0.2.2:8000`), and all user-facing strings
    - Create `lib/core/constants/app_text_styles.dart` with Poppins headings and Inter body text styles
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

  - [ ] 7.2 Create error handling classes
    - Create `lib/core/errors/app_exception.dart` with `AppException`, `UnauthorizedException`, `NotFoundException`, `ServerException`, `NetworkException`
    - Create `lib/core/errors/failure.dart` with simple `Failure` class
    - _Requirements: 11.3, 11.4, 11.5, 11.6_

  - [ ] 7.3 Implement secure storage wrapper
    - Create `lib/core/storage/secure_storage.dart` wrapping `FlutterSecureStorage`
    - Methods: saveAccessToken, getAccessToken, saveRefreshToken, getRefreshToken, saveUserInfo (partyCode, fullName), getPartyCode, getFullName, clearAll
    - Create `secureStorageProvider` Riverpod Provider
    - _Requirements: 12.1, 12.2, 12.3_

  - [ ] 7.4 Implement API client and interceptors
    - Create `lib/core/network/api_client.dart` with Dio wrapper, base URL, timeouts (30s connect, 30s receive)
    - Create `lib/core/network/interceptors/auth_interceptor.dart` — attach Bearer token on requests, handle 401 with refresh flow (queue concurrent requests, 10s timeout, retry or logout)
    - Create `lib/core/network/interceptors/error_interceptor.dart` — map DioException types to typed AppExceptions
    - Create `apiClientProvider` Riverpod Provider
    - _Requirements: 2.1, 2.2, 2.3, 2.5, 11.3, 11.4, 11.5, 11.6_

  - [ ] 7.5 Create utility classes
    - Create `lib/core/utils/date_formatter.dart` with `formatDate(String?)` → "dd MMM yyyy" and `formatDateLong(String?)` → "dd MMMM yyyy", returning "—" for null/empty
    - Create `lib/core/utils/validators.dart` with username (not empty) and password (not empty, min 6 chars) validators
    - _Requirements: 4.4, 7.5, 7.6_

- [ ] 8. Flutter auth feature
  - [ ] 8.1 Create auth models and repository
    - Create `lib/features/auth/data/models/auth_model.dart` with `LoginRequest` (toJson) and `TokenResponse` (fromJson, snake_case → camelCase)
    - Create `lib/features/auth/data/repositories/auth_repository.dart` with login, refreshToken, logout methods
    - Store tokens and user info in SecureStorage on successful login
    - Create `authRepositoryProvider` Riverpod Provider
    - _Requirements: 1.1, 1.8, 3.1, 3.2_

  - [ ] 8.2 Implement auth state provider
    - Create `lib/features/auth/providers/auth_provider.dart`
    - Define `AuthStatus` enum (initial, authenticated, unauthenticated, loading) and `AuthState` class
    - Implement `AuthNotifier extends StateNotifier<AuthState>` with checkAuthStatus, login, logout methods
    - checkAuthStatus reads tokens from storage — if access token exists, set authenticated
    - Create `authProvider = StateNotifierProvider<AuthNotifier, AuthState>`
    - _Requirements: 1.5, 1.6, 1.8, 3.2, 3.3_

  - [ ] 8.3 Implement login screen and widgets
    - Create `lib/features/auth/presentation/widgets/logo_header.dart` with app icon and title
    - Create `lib/features/auth/presentation/widgets/login_form.dart` as ConsumerStatefulWidget with form validation, password visibility toggle, loading state in button
    - Create `lib/features/auth/presentation/screens/login_screen.dart` composing LogoHeader + LoginForm, listening for auth errors → SnackBar
    - Disable login button during loading, show CircularProgressIndicator inside button
    - _Requirements: 1.5, 1.6, 1.7, 1.8, 1.11, 11.3_

- [ ] 9. Flutter orders feature
  - [ ] 9.1 Create order models and repository
    - Create `lib/features/orders/data/models/order_model.dart` with `OrderModel` (fromJson, toJson) and `OrderListResponse` (fromJson)
    - Create `lib/features/orders/data/repositories/order_repository.dart` with fetchOrders(search, sortBy, sortOrder) and fetchOrderById(id)
    - Create `orderRepositoryProvider` Riverpod Provider
    - _Requirements: 4.1, 4.3, 7.1_

  - [ ] 9.2 Implement orders state provider
    - Create `lib/features/orders/providers/order_provider.dart`
    - Define `OrdersState` with `AsyncValue<List<OrderModel>>` orders and searchQuery
    - Implement `OrdersNotifier extends StateNotifier<OrdersState>` with fetchOrders, filterBySearch (client-side, 400ms debounce), refresh
    - Create `ordersProvider` and `orderDetailProvider = FutureProvider.family<OrderModel, int>`
    - _Requirements: 4.3, 4.5, 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ] 9.3 Implement dispatch status badge widget
    - Create `lib/features/orders/presentation/widgets/dispatch_status_badge.dart`
    - Map dispatch_status to display label and colors (case-insensitive comparison)
    - Pending/Processing/Awaiting Dispatch → "Not Dispatched" amber
    - Dispatched → blue, Delivered → green, Cancelled → red
    - Null/empty/unknown → "Status Unavailable" grey
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_

  - [ ] 9.4 Implement order list screen and widgets
    - Create `lib/features/orders/presentation/widgets/order_card.dart` showing order_no, formatted dates, dispatch status badge, chevron
    - Create `lib/features/orders/presentation/widgets/order_search_bar.dart` with 400ms debounce, max 50 chars
    - Create `lib/features/orders/presentation/widgets/empty_orders_state.dart` with icon and "No orders found" message
    - Create `lib/features/orders/presentation/screens/orders_screen.dart` with AppBar (title, party name, profile icon), search bar, order count, RefreshIndicator, ListView with shimmer loading (6 skeleton cards)
    - _Requirements: 4.3, 4.4, 4.5, 4.6, 4.7, 4.9, 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ] 9.5 Implement order detail screen
    - Create `lib/features/orders/presentation/screens/order_detail_screen.dart`
    - Dispatch status banner: green with checkmark (Dispatched/Delivered) or amber with clock (Pending/Processing/Awaiting Dispatch) or grey for unknown
    - Order information section: order_no, order_date, Display_Status badge
    - Dispatch details section: dispatch_status, dispatch_date, invoice_no, tracking_no (show "—" for null)
    - Remarks section: shown only when remarks has non-whitespace content
    - Loading indicator, error state with retry, 10s timeout handling
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.11, 7.12, 7.13_

- [ ] 10. Flutter profile feature and shared widgets
  - [ ] 10.1 Implement profile screen
    - Create `lib/features/profile/data/models/profile_model.dart` with `ProfileModel` (fromJson)
    - Create `lib/features/profile/presentation/screens/profile_screen.dart`
    - Avatar circle with initials derived from full_name (split on first space, uppercase first chars)
    - Display full_name, username, party_code, email (or "—" for null/empty fields)
    - Logout button (outlined, red, full width) — clears storage, navigates to login
    - Create `profileProvider = FutureProvider<ProfileModel>`
    - Error state with retry, loading indicator
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 3.1, 3.2, 3.3, 3.4, 3.5_

  - [ ] 10.2 Create shared widgets
    - Create `lib/shared/widgets/loading_overlay.dart` for generic loading indicator
    - Create `lib/shared/widgets/error_widget.dart` with error message and retry button
    - Create `lib/shared/widgets/app_scaffold.dart` for consistent page structure
    - _Requirements: 4.9, 7.12, 9.5_

- [ ] 11. Flutter router and app entry point
  - [ ] 11.1 Implement app router
    - Create `lib/core/router/app_router.dart` with GoRouter configuration
    - Routes: `/login` → LoginScreen, `/orders` → OrdersScreen, `/orders/:id` → OrderDetailScreen, `/profile` → ProfileScreen
    - Redirect logic: unauthenticated + not on login → `/login`; authenticated + on login → `/orders`
    - `refreshListenable` tied to auth state changes
    - Create `routerProvider`
    - _Requirements: 1.5, 1.6, 1.8, 3.3_

  - [ ] 11.2 Implement app entry point
    - Create `lib/main.dart` with WidgetsFlutterBinding, ProviderScope, and app widget
    - Create `lib/app.dart` as ConsumerWidget with MaterialApp.router, theme configuration (Google Fonts, AppColors), debugShowCheckedModeBanner: false
    - _Requirements: 1.5, 1.6_

- [ ] 12. Checkpoint - Verify full application builds
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 13. Backend property-based tests
  - [ ]* 13.1 Write property test for JWT claims integrity
    - **Property 1: JWT claims integrity**
    - Use Hypothesis to generate random usernames and party_codes
    - Verify issued tokens decode to exact username as `sub` and correct `party_code`
    - **Validates: Requirements 1.4**

  - [ ]* 13.2 Write property test for account lockout enforcement
    - **Property 2: Account lockout enforcement**
    - Use Hypothesis to generate random usernames and attempt sequences
    - Verify that after 5 failures, all attempts within 15 minutes are rejected
    - **Validates: Requirements 1.9**

  - [ ]* 13.3 Write property test for refresh token type validation
    - **Property 3: Refresh token type validation**
    - Use Hypothesis to generate JWTs with wrong types, expired tokens, malformed tokens
    - Verify Backend returns 401 and never issues new access token
    - **Validates: Requirements 2.4, 2.6**

  - [ ]* 13.4 Write property test for party-isolated order access
    - **Property 4: Party-isolated order access**
    - Use Hypothesis to generate random party_codes and order sets
    - Verify list queries return only matching party_code orders
    - Verify individual order requests for wrong party return 403
    - **Validates: Requirements 4.1, 7.9, 10.1, 10.2, 10.3, 10.4, 10.6**

  - [ ]* 13.5 Write property test for order sorting correctness
    - **Property 5: Order sorting correctness**
    - Use Hypothesis to generate random order lists with various sort params
    - Verify orders are sorted correctly with stable secondary sort by id desc
    - **Validates: Requirements 4.2, 6.1, 6.2, 6.5**

  - [ ]* 13.6 Write property test for error response format compliance
    - **Property 12: Error response format compliance**
    - Trigger various error conditions and verify response format {"detail": "<message>"}
    - Verify message ≤ 150 chars, no stack traces, no internal paths
    - **Validates: Requirements 11.1, 11.2**

  - [ ]* 13.7 Write property test for protected endpoint token validation
    - **Property 13: Protected endpoint token validation**
    - Use Hypothesis to generate malformed/expired/wrong-type tokens
    - Verify all protected endpoints return 401
    - **Validates: Requirements 13.7**

  - [ ]* 13.8 Write property test for request body validation
    - **Property 14: Request body validation**
    - Use Hypothesis to generate invalid request bodies (missing fields, wrong types)
    - Verify Backend returns 422 with field-level error info
    - **Validates: Requirements 13.10**

- [ ] 14. Flutter property-based tests
  - [ ]* 14.1 Write property test for client-side order search filtering
    - **Property 6: Client-side order search filtering**
    - Use glados to generate random order lists and search strings
    - Verify filtered result contains exactly orders with case-insensitive substring match, preserving order
    - **Validates: Requirements 5.1, 5.3**

  - [ ]* 14.2 Write property test for dispatch status mapping
    - **Property 7: Dispatch status mapping**
    - Use glados to generate random strings (all casings, empty, null, unknown values)
    - Verify correct mapping to display label and colors
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7**

  - [ ]* 14.3 Write property test for date formatting correctness
    - **Property 8: Date formatting correctness**
    - Use glados to generate random valid ISO date strings
    - Verify `formatDate` → "dd MMM yyyy" and `formatDateLong` → "dd MMMM yyyy", null/empty → "—"
    - **Validates: Requirements 4.4, 7.5**

  - [ ]* 14.4 Write property test for null field display
    - **Property 9: Null field display**
    - Use glados to generate OrderModels with nullable fields
    - Verify null/empty fields render as "—"
    - **Validates: Requirements 7.6, 9.6**

  - [ ]* 14.5 Write property test for remarks section visibility
    - **Property 10: Remarks section visibility**
    - Use glados to generate random strings (whitespace-only, empty, content)
    - Verify section is visible only when remarks has non-whitespace content
    - **Validates: Requirements 7.7, 7.8**

  - [ ]* 14.6 Write property test for avatar initials derivation
    - **Property 11: Avatar initials derivation**
    - Use glados to generate random full_name strings
    - Verify initials: split on first space → two uppercase chars; no space → one uppercase char
    - **Validates: Requirements 9.2**

  - [ ]* 14.7 Write property test for error message fallback
    - **Property 12: Error response client-side handling**
    - Use glados to generate random response bodies (with/without "detail" field)
    - Verify fallback "Something went wrong. Please try again." when detail is missing
    - **Validates: Requirements 11.6**

- [ ] 15. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- All Flutter imports use `package:balar/...` (NOT `package:order_tracker/`)
- NO freezed, NO code generation, NO build_runner — all models are manual
- All Riverpod providers are written manually (StateNotifierProvider, FutureProvider, etc.)
- Backend uses async SQLAlchemy with aiosqlite throughout
- Error responses always follow `{"detail": "message"}` format

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "7.1", "7.2"] },
    { "id": 1, "tasks": ["1.3", "2.1", "7.3"] },
    { "id": 2, "tasks": ["1.4", "2.2", "7.5"] },
    { "id": 3, "tasks": ["3.1", "3.2", "7.4"] },
    { "id": 4, "tasks": ["4.1", "4.2", "4.3", "8.1"] },
    { "id": 5, "tasks": ["5.1", "5.2", "8.2"] },
    { "id": 6, "tasks": ["8.3", "9.1", "10.2"] },
    { "id": 7, "tasks": ["9.2", "9.3"] },
    { "id": 8, "tasks": ["9.4", "9.5", "10.1"] },
    { "id": 9, "tasks": ["11.1", "11.2"] },
    { "id": 10, "tasks": ["13.1", "13.2", "13.3", "13.4", "13.5", "13.6", "13.7", "13.8"] },
    { "id": 11, "tasks": ["14.1", "14.2", "14.3", "14.4", "14.5", "14.6", "14.7"] }
  ]
}
```
