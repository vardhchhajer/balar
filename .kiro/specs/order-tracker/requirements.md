# Requirements Document

## Introduction

Order Tracker is a B2B mobile application that allows business customers (parties) to log in with company-assigned credentials and track their orders in real-time. Each customer can only view orders belonging to their own party_code, ensuring strict data isolation between business entities. The system consists of a Flutter mobile app and a FastAPI backend with JWT-based authentication.

## Glossary

- **App**: The Order Tracker Flutter mobile application (project name: `balar`) running on Android and iOS
- **Backend**: The FastAPI Python server providing REST API endpoints for authentication, orders, and profile data
- **Customer**: A business user who logs into the App using company-assigned credentials to track orders
- **Party**: A business entity identified by a unique party_code; all Customers and Orders belong to exactly one Party
- **Party_Code**: A unique string identifier that links a Customer to their Party and their Orders
- **JWT**: JSON Web Token used for stateless authentication, containing claims such as username and party_code
- **Access_Token**: A short-lived JWT (1 hour expiry) used to authenticate API requests
- **Refresh_Token**: A longer-lived JWT (7 days expiry) used to obtain a new Access_Token without re-authentication
- **Dispatch_Status**: The current fulfillment state of an Order: Pending, Processing, Awaiting Dispatch, Dispatched, Delivered, or Cancelled
- **Display_Status**: The user-facing simplified status label derived from Dispatch_Status: Not Dispatched, Dispatched, Delivered, or Cancelled
- **Secure_Storage**: Platform-specific encrypted storage (iOS Keychain, Android Keystore) used to persist tokens
- **Auth_Interceptor**: A Dio HTTP interceptor that attaches Access_Tokens to requests and handles automatic token refresh on 401 responses
- **Order**: A record representing a business transaction belonging to a Party, identified by a unique order_no

## Requirements

### Requirement 1: Customer Authentication

**User Story:** As a Customer, I want to log in with my company-assigned username and password, so that I can securely access my order information.

#### Acceptance Criteria

1. WHEN a Customer submits valid credentials, THE Backend SHALL return an Access_Token with 1 hour expiry and a Refresh_Token with 7 day expiry
2. WHEN a Customer submits invalid credentials, THE Backend SHALL return a 401 response with the message "Invalid username or password."
3. THE Backend SHALL hash all passwords using bcrypt with cost factor 12
4. THE Backend SHALL include the username and party_code as claims within the JWT payload
5. WHEN the App starts, IF a non-expired Access_Token exists in Secure_Storage, THEN THE App SHALL navigate directly to the orders screen without requiring login
6. WHEN the App starts, IF no Access_Token exists in Secure_Storage or the stored Access_Token has expired, THEN THE App SHALL display the login screen
7. WHILE a login request is in progress, THE App SHALL display a loading indicator within the login button and disable the login button to prevent duplicate submissions
8. WHEN authentication succeeds, THE App SHALL store the Access_Token and Refresh_Token in Secure_Storage and navigate to the orders screen
9. IF a Customer submits invalid credentials 5 consecutive times for the same username, THEN THE Backend SHALL reject further login attempts for that username for 15 minutes and return an error indicating the account is temporarily locked
10. WHEN the Access_Token has expired and a valid Refresh_Token exists in Secure_Storage, THE App SHALL request a new Access_Token from the Backend using the Refresh_Token without requiring Customer interaction
11. IF a login request fails due to a network error, THEN THE App SHALL display an error message indicating the network is unavailable and allow the Customer to retry

### Requirement 2: Automatic Token Refresh

**User Story:** As a Customer, I want my session to remain active without re-entering credentials, so that I can use the app uninterrupted during the refresh token validity period.

#### Acceptance Criteria

1. WHEN the Backend returns a 401 response to an API request, THE Auth_Interceptor SHALL attempt to obtain a new Access_Token using the stored Refresh_Token within 10 seconds
2. WHEN the token refresh succeeds, THE Auth_Interceptor SHALL store the new Access_Token in Secure_Storage and retry all requests that received a 401 during the refresh operation, using the new token in the order they were queued
3. IF the token refresh request returns a non-2xx response, a network error occurs, or the 10-second timeout elapses, THEN THE App SHALL clear all stored tokens from Secure_Storage and navigate the Customer to the login screen
4. THE Backend SHALL validate that the Refresh_Token has type "refresh" before issuing a new Access_Token
5. WHILE a token refresh operation is in progress, THE Auth_Interceptor SHALL queue subsequent requests that receive a 401 response rather than initiating additional refresh attempts
6. IF the Backend determines the Refresh_Token is invalid, expired, or not of type "refresh", THEN THE Backend SHALL return a 401 response with an error indication specifying the reason for rejection

### Requirement 3: Customer Logout

**User Story:** As a Customer, I want to log out of the application, so that my session is terminated and my credentials are cleared from the device.

#### Acceptance Criteria

1. WHEN the Customer taps the logout button, THE App SHALL send a logout request to the Backend and await a response for no longer than 10 seconds
2. WHEN logout completes successfully, THE App SHALL clear all authentication tokens, refresh tokens, and cached user profile data from Secure_Storage
3. WHEN logout completes, THE App SHALL navigate the Customer to the login screen and clear the navigation stack so that the back button does not return to authenticated screens
4. IF the logout request to the Backend fails or exceeds the 10-second timeout, THEN THE App SHALL clear all local authentication data from Secure_Storage, navigate the Customer to the login screen, and display a message indicating the remote session could not be terminated
5. WHILE a logout request is in progress, THE App SHALL disable the logout button to prevent duplicate requests

### Requirement 4: Party-Isolated Order Listing

**User Story:** As a Customer, I want to see all orders belonging to my party, so that I can monitor the status of my business orders.

#### Acceptance Criteria

1. THE Backend SHALL filter all order queries by the party_code extracted from the authenticated Customer's JWT
2. THE Backend SHALL return orders sorted by order_date descending, including the total count in the response
3. WHEN the orders screen loads, THE App SHALL fetch and display all orders belonging to the Customer's Party
4. THE App SHALL display each order as a card showing order_no, order_date formatted as "dd MMM yyyy", dispatch_date formatted as "dd MMM yyyy" (or "—" if null), and Display_Status badge
5. WHEN a Customer pulls down on the order list, THE App SHALL refresh the order data from the Backend
6. WHILE orders are loading, THE App SHALL display 6 shimmer skeleton placeholder cards
7. WHEN no orders exist for the Customer's Party, THE App SHALL display an empty state with an icon and "No orders found" message
8. IF the JWT does not contain a valid party_code, THEN THE Backend SHALL reject the request with an authentication error response
9. IF the order fetch request fails due to a network or server error, THEN THE App SHALL display an error message with a retry option

### Requirement 5: Order Search

**User Story:** As a Customer, I want to search my orders by order number, so that I can quickly find a specific order.

#### Acceptance Criteria

1. THE App SHALL provide a search bar that accepts text input up to 50 characters and filters orders by order_no on the client side
2. WHEN the Customer types in the search bar, THE App SHALL debounce the input by 400 milliseconds before applying the filter
3. WHEN the search text matches a substring of an order's order_no (case-insensitive), THE App SHALL include that order in the filtered results displayed in the same list format as unfiltered orders
4. WHEN the search text does not match any orders, THE App SHALL display a message stating "No orders found" in place of the order list
5. WHEN the Customer clears the search bar (empty string), THE App SHALL display all orders in their default order

### Requirement 6: Order Sorting

**User Story:** As a Customer, I want my orders sorted by date, so that I can see the most recent orders first.

#### Acceptance Criteria

1. THE Backend SHALL accept a sort_by parameter limited to the values "order_date" or "dispatch_date", defaulting to "order_date" when the parameter is omitted
2. THE Backend SHALL accept a sort_order parameter limited to the values "asc" or "desc", defaulting to "desc" when the parameter is omitted
3. WHEN no sort parameters are specified, THE Backend SHALL return orders sorted by order_date in descending order
4. IF sort_by or sort_order contains a value other than the accepted values, THEN THE Backend SHALL reject the request with an error message indicating the invalid parameter value
5. WHEN multiple orders share the same sort field value, THE Backend SHALL apply a stable secondary sort by order identifier in descending order to ensure deterministic results

### Requirement 7: Order Detail View

**User Story:** As a Customer, I want to view the full details of an order, so that I can see dispatch status, invoice number, tracking number, and remarks.

#### Acceptance Criteria

1. WHEN a Customer taps an order card, THE App SHALL display a loading indicator and navigate to the order detail screen showing the dispatch status banner, order information section, dispatch details section, and remarks section (if applicable)
2. THE App SHALL display the dispatch status banner as a full-width section at the top of the detail screen
3. IF the order's Dispatch_Status is "Dispatched" or "Delivered", THEN THE App SHALL display the banner with a green background and checkmark icon showing the dispatch_date formatted as "dd MMMM yyyy"
4. IF the order's Dispatch_Status is "Pending", "Processing", or "Awaiting Dispatch", THEN THE App SHALL display the banner with an amber background and clock icon showing "Your order is being processed"
5. THE App SHALL display order information including order_no, order_date formatted as "dd MMMM yyyy", and Display_Status badge
6. THE App SHALL display dispatch details including dispatch_status, dispatch_date formatted as "dd MMMM yyyy", invoice_no, and tracking_no, showing "—" for null or empty values
7. WHEN the order has remarks containing at least one non-whitespace character, THE App SHALL display a remarks section with the remarks text
8. WHEN the order has null, empty, or whitespace-only remarks, THE App SHALL hide the remarks section
9. WHEN a Customer requests an order belonging to a different Party, THE Backend SHALL return a 403 response with "Access denied."
10. WHEN a Customer requests an order that does not exist, THE Backend SHALL return a 404 response with "Order not found."
11. IF the order's Dispatch_Status does not match any of "Dispatched", "Delivered", "Pending", "Processing", or "Awaiting Dispatch", THEN THE App SHALL display the banner with a grey background and the Dispatch_Status value as text
12. IF the order detail request fails due to a network error or the Backend returns a 5xx response, THEN THE App SHALL display an error message indicating the details could not be loaded and offer a retry option
13. IF the order detail request does not receive a response within 10 seconds, THEN THE App SHALL cancel the request, dismiss the loading indicator, and display a timeout error message with a retry option

### Requirement 8: Dispatch Status Display Mapping

**User Story:** As a Customer, I want to see a simplified, color-coded dispatch status, so that I can quickly understand the current state of my order.

#### Acceptance Criteria

1. WHEN the Dispatch_Status is "Pending", "Processing", or "Awaiting Dispatch", THE App SHALL display "Not Dispatched" with amber background (#FFF3CD) and dark amber text (#856404)
2. WHEN the Dispatch_Status is "Dispatched", THE App SHALL display "Dispatched" with blue background (#D1ECF1) and dark blue text (#0C5460)
3. WHEN the Dispatch_Status is "Delivered", THE App SHALL display "Delivered" with green background (#D4EDDA) and dark green text (#155724)
4. WHEN the Dispatch_Status is "Cancelled", THE App SHALL display "Cancelled" with red background (#F8D7DA) and dark red text (#721C24)
5. IF the Dispatch_Status value is null, empty, or undefined, THEN THE App SHALL display "Status Unavailable" with grey background (#E2E3E5) and dark grey text (#383D41)
6. IF the Dispatch_Status contains a value not matching any of "Pending", "Processing", "Awaiting Dispatch", "Dispatched", "Delivered", or "Cancelled", THEN THE App SHALL display "Status Unavailable" with grey background (#E2E3E5) and dark grey text (#383D41)
7. THE App SHALL perform case-insensitive comparison when matching the Dispatch_Status value to the defined status strings

### Requirement 9: Customer Profile

**User Story:** As a Customer, I want to view my profile information, so that I can verify my account details and party association.

#### Acceptance Criteria

1. WHEN the Customer navigates to the profile screen, THE App SHALL display the Customer's full_name, username, party_code, and email within 2 seconds of navigation
2. WHEN the profile screen is displayed, THE App SHALL display an avatar circle containing the first character of the Customer's first name and the first character of the Customer's last name as uppercase letters, derived by splitting full_name on the first space; IF full_name contains no space, THEN THE App SHALL display only the first character of full_name as an uppercase letter
3. WHEN the App requests the authenticated Customer's profile, THE Backend SHALL return the Customer's profile data including id, username, full_name, email, and party_code
4. IF the Customer's authentication token is missing or invalid when navigating to the profile screen, THEN THE App SHALL redirect the Customer to the login screen without displaying profile data
5. IF the Backend fails to return profile data due to a network or server error, THEN THE App SHALL display an error message indicating that profile information could not be loaded and provide a retry option
6. IF any profile field value is null or empty in the Backend response, THEN THE App SHALL display a placeholder dash character ("—") in place of the missing field value

### Requirement 10: Party Data Isolation

**User Story:** As a Customer, I want assurance that I can only see my own party's data, so that business confidentiality is maintained between parties.

#### Acceptance Criteria

1. THE Backend SHALL extract party_code exclusively from the authenticated JWT claims for all order queries
2. THE Backend SHALL never accept a client-provided party_code supplied via any request mechanism (query parameters, request body, or headers) for filtering orders
3. WHEN a Customer requests an individual order, THE Backend SHALL verify the order's party_code matches the JWT party_code before returning data
4. IF the order's party_code does not match the authenticated Customer's party_code, THEN THE Backend SHALL return a 403 Access Denied response with a response body that does not confirm nor deny the existence of the requested order
5. IF the authenticated JWT does not contain a party_code claim or the claim value is empty, THEN THE Backend SHALL reject the request with an access denied response and return no order data
6. WHEN a Customer requests a list of orders, THE Backend SHALL return only orders whose party_code matches the authenticated JWT party_code

### Requirement 11: Secure Error Handling

**User Story:** As a Customer, I want clear error messages without technical details, so that I understand issues without exposing system internals.

#### Acceptance Criteria

1. THE Backend SHALL return all error responses in the format {"detail": "<message>"} where the message is a plain-language sentence of no more than 150 characters, free of technical jargon, stack traces, internal paths, or variable names
2. THE Backend SHALL never expose stack traces, internal paths, database identifiers, environment variables, or library version numbers in error responses
3. WHEN the App receives an HTTP 4xx or 5xx response, THE App SHALL display the "detail" value from the response body in a SnackBar notification that remains visible for 4 seconds
4. WHEN a network request receives no response within 10 seconds, THE App SHALL display "Unable to connect. Please check your internet connection." in a SnackBar notification
5. WHEN the App receives an HTTP 5xx response, THE App SHALL display the "detail" value from the response body in the SnackBar notification
6. IF the App receives an error response that does not contain a parseable "detail" field, THEN THE App SHALL display a generic fallback message "Something went wrong. Please try again." in a SnackBar notification

### Requirement 12: Secure Token Storage

**User Story:** As a Customer, I want my authentication tokens stored securely on my device, so that unauthorized apps cannot access my session.

#### Acceptance Criteria

1. THE App SHALL store Access_Token and Refresh_Token exclusively in Secure_Storage (iOS Keychain, Android Keystore)
2. THE App SHALL never store tokens in plain text, shared preferences, or local storage
3. WHEN the Customer logs out, THE App SHALL delete all tokens, cached credentials, and session identifiers from Secure_Storage within 2 seconds of the logout request
4. IF Secure_Storage is unavailable or inaccessible on the device, THEN THE App SHALL refuse to store tokens and SHALL prevent the Customer from completing authentication, displaying an error message indicating that secure storage is required
5. IF token deletion from Secure_Storage fails during logout, THEN THE App SHALL retry deletion up to 3 times, and if still unsuccessful, SHALL invalidate the local session and inform the Customer that a manual sign-out from account settings may be required

### Requirement 13: Backend API Structure

**User Story:** As a developer, I want a well-structured REST API, so that the mobile app can reliably communicate with the backend.

#### Acceptance Criteria

1. THE Backend SHALL expose POST /auth/login accepting username and password in the request body, returning an Access_Token and a Refresh_Token on successful credential validation
2. THE Backend SHALL expose POST /auth/refresh accepting a Refresh_Token via Authorization header, returning a new Access_Token
3. THE Backend SHALL expose POST /auth/logout accepting an Access_Token, returning a success message
4. THE Backend SHALL expose GET /orders accepting optional query parameters: search (string), sort_by (one of: "order_date", "dispatch_date"), and sort_order ("asc" or "desc", default "desc"), requiring authentication
5. THE Backend SHALL expose GET /orders/{order_id} returning a single order's details, requiring authentication
6. THE Backend SHALL expose GET /profile returning the authenticated Customer's profile, requiring authentication
7. WHEN a request to a protected endpoint includes an Access_Token that is missing, malformed, expired, or not of type "access", THE Backend SHALL reject the request with HTTP 401 status and an error response indicating the authentication failure reason
8. WHILE in development mode, THE Backend SHALL enable CORS for all origins
9. IF a requested resource does not exist (e.g., order_id not found), THEN THE Backend SHALL respond with HTTP 404 status and an error response indicating the resource was not found
10. IF a request body is missing required fields or contains values outside accepted ranges, THEN THE Backend SHALL respond with HTTP 422 status and an error response identifying which fields failed validation

### Requirement 14: Mock Data Seeding

**User Story:** As a developer, I want pre-populated test data, so that I can develop and test the application without manual data entry.

#### Acceptance Criteria

1. WHEN the Backend starts and the customer_users table contains zero records, THE Backend SHALL create database tables and seed mock data
2. THE Backend SHALL seed 2 test users: testuser1 (password "password123", party_code PARTY001, full_name "Rajesh Kumar") and testuser2 (password "password123", party_code PARTY002, full_name "Suresh Patel") with bcrypt-hashed passwords
3. THE Backend SHALL seed 15 orders: 10 orders for PARTY001 and 5 orders for PARTY002, distributed across at least 3 distinct dispatch statuses (Pending, Dispatched, Delivered, Processing, Cancelled), with each status represented by at least 1 order
4. WHEN the Backend starts and the customer_users table already contains one or more records, THE Backend SHALL skip the seeding process and leave existing data unchanged
