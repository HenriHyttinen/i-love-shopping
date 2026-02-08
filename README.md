# i-love-shopping (Part 2)

## Overview
Hardware-focused B2C e-commerce platform with Foundation + Commerce layers.  
This version includes secure accounts and authentication (email + Google OAuth, JWT with refresh rotation, optional 2FA), searchable catalog, guest and persistent carts, single-page checkout, payment sandbox simulation, order management, and Dockerized setup.

## ERD
ERD image: `docs/erd.svg`

Mermaid source:

```mermaid
erDiagram
    USER {
        int id PK
        string email
        string full_name
        string otp_secret
        boolean is_2fa_enabled
        datetime date_joined
    }

    CATEGORY {
        int id PK
        string name
        string slug
    }

    BRAND {
        int id PK
        string name
    }

    PRODUCT {
        int id PK
        string name
        string description
        decimal price
        int stock_quantity
        decimal rating
        decimal weight_kg
        decimal weight_lb
        decimal length_cm
        decimal width_cm
        decimal height_cm
        decimal length_in
        decimal width_in
        decimal height_in
    }

    PRODUCT_IMAGE {
        int id PK
        string image
        string alt_text
    }

    CATEGORY ||--o{ PRODUCT : has
    BRAND ||--o{ PRODUCT : has
    PRODUCT ||--o{ PRODUCT_IMAGE : has
```
Crowfoot notation is used for cardinality/modality:
- `||` = exactly one (mandatory)
- `o{` = zero or many (optional many)

Commerce extension:

```mermaid
erDiagram
    CART {
        int id PK
        int user_id FK
        string guest_token
    }
    CART_ITEM {
        int id PK
        int cart_id FK
        int product_id FK
        int quantity
        decimal unit_price
    }
    ORDER {
        int id PK
        int user_id FK
        string status
        string payment_method
        decimal subtotal
        decimal shipping_cost
        decimal total
        text encrypted_shipping_address
    }
    ORDER_ITEM {
        int id PK
        int order_id FK
        int product_id FK
        int quantity
        decimal unit_price
    }
    PAYMENT_TRANSACTION {
        int id PK
        int order_id FK
        string provider
        string status
        string failure_code
        text encrypted_provider_payload
    }
    PAYMENT_STATUS_MESSAGE {
        int id PK
        int order_id FK
        int transaction_id FK
        string status
        datetime consumed_at
    }

    CART ||--o{ CART_ITEM : has
    PRODUCT ||--o{ CART_ITEM : in
    ORDER ||--o{ ORDER_ITEM : has
    PRODUCT ||--o{ ORDER_ITEM : purchased_as
    ORDER ||--|| PAYMENT_TRANSACTION : has
    ORDER ||--o{ PAYMENT_STATUS_MESSAGE : emits
    PAYMENT_TRANSACTION ||--o{ PAYMENT_STATUS_MESSAGE : publishes
```

## Architecture & Scalability
- Architectural style: modular monolith (Django + REST). The `users` and `catalog` apps are cleanly separated and can be split into services if needed.
- Scaling path: stateless API with JWT allows horizontal scaling behind a load balancer; Postgres can scale with read replicas and connection pooling.
- Caching: safe to add Redis for hot catalog queries and token/session metadata without changing API contracts.

## Database & ACID Notes
- Default local DB: SQLite for quick dev. Docker uses Postgres for production-like behavior.
- ACID matters here because orders/payments/inventory must be consistent even with concurrent requests and failures:
  - Atomicity: multi-step updates (e.g., stock + order rows) must succeed or roll back together.
  - Consistency: constraints + foreign keys keep data valid after every transaction.
  - Isolation: concurrent checkouts won't corrupt stock counts.
  - Durability: committed orders survive server restarts.
- Postgres supports transaction isolation levels, robust indexing, and scaling strategies (read replicas, partitioning).

## JWT Notes (Reviewer-Friendly)
JWT = `header.payload.signature` (base64url):
- Header: signing algorithm and token type.
- Payload: claims like user id, issued-at (`iat`), expiration (`exp`), token id (`jti`).
- Signature: verifies integrity and authenticity (server secret).
This project uses short-lived access tokens + rotated refresh tokens with blacklist protection.

## Auth & Security Notes
- Access tokens live in memory only (mini frontend) and are short-lived.
- Refresh tokens rotate on every refresh, with blacklist after rotation.
- Access token revocation uses a blocklist to reject revoked JWTs.
- Registration is protected with reCAPTCHA when a secret key is configured.
- Optional user-enabled 2FA (TOTP) for stronger account security.

## Search & Relevance
- `search` uses DRF full-text search across name, description, brand, category.
- Sorting supports `price`, `rating`, `name`, and `relevance`.
- `ordering=relevance` applies a simple rank: name prefix match > name contains > description/brand/category contains.

## Testing Strategy
Automated tests cover:
- Auth: registration, login, 2FA, refresh rotation, token revocation, logout flows.
- Catalog: filtering, ordering, suggestions, image upload permissions.
- Commerce: cart item/total behavior, guest checkout and payment outcomes, prefill flow, order filtering, cancellation/inventory restore.
- Security: invalid filters, injection-like input, invalid ordering.

Manual checks (recommended for demo):
- CAPTCHA: registration requires a valid token when secret key is set.
- OAuth: Google login with access token exchange.
- 2FA: setup → verify → login with 2FA enabled → disable.

Latest verification in this repo revision:
- Python static compile check passed for updated backend modules and tests.
- Full Django test execution requires dependencies installed (`pip install -r backend/requirements.txt`) and DB migration applied.

## Setup for OAuth (Google)
1) Go to Google Cloud Console → APIs & Services → Credentials.
2) Create OAuth client ID (Web Application).
3) Authorized JavaScript origins:
   - `http://localhost:8000`
4) Authorized redirect URIs:
   - `http://localhost:8000`
   - `http://localhost:8000/api/auth/oauth/google/`
5) Copy Client ID/Secret into `backend/.env`:
   - `GOOGLE_OAUTH_CLIENT_ID=...`
   - `GOOGLE_OAUTH_CLIENT_SECRET=...`
6) In Google Cloud Console, enable the “Google People API” if required.
7) Mini frontend: paste the Client ID into the Google OAuth section to test login.
   - The mini frontend will auto-load it from `/api/auth/oauth/google-client-id/`.
   - Demo flow uses a redirect-based OAuth code exchange for better browser compatibility.
   - OAuth changes can take several minutes to propagate; hard reload after updates.
8) Existing accounts can be linked by email (SOCIALACCOUNT_QUERY_EMAIL).
   - Social account adapter will auto-connect existing users by email.

## Password Reset Email
This project uses SMTP. Update these values in `backend/.env`:
```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=1
DEFAULT_FROM_EMAIL=noreply@hardware-shop.test
```
Endpoints:
- `POST /api/auth/password/reset/`
- `POST /api/auth/password/reset/confirm/`

## reCAPTCHA Setup
- Add both keys to `backend/.env`:
  - `RECAPTCHA_SITE_KEY=...`
  - `RECAPTCHA_SECRET_KEY=...`
- Mini frontend auto-loads the site key from `/api/auth/recaptcha-site-key/`.

## Common Setup Issues
- Backend fails on startup: check `.env` values and run migrations.
- OAuth fails: verify redirect URI matches exactly and client ID/secret are correct.
- OAuth redirect_uri_mismatch: ensure the exact origin (`http://localhost:8000`) is listed as an authorized redirect URI and wait for Google to propagate changes.
- CAPTCHA fails: ensure `RECAPTCHA_SECRET_KEY` is set (empty key skips validation).
- Docker port 5432 in use: stop local Postgres or change the Docker port mapping.
- docker-compose v1 ContainerConfig error: run `docker-compose down --remove-orphans` and `docker-compose rm -f`.

## Setup Instructions

### Docker (recommended)
1) Copy env template
```
cp backend/envtemplate.txt backend/.env
```
2) Fill in Google OAuth + reCAPTCHA secrets in `backend/.env`.
   - Google OAuth redirect URIs: `http://localhost:8000` and `http://localhost:8000/api/auth/oauth/google/`
   - Allowed JS origins: `http://localhost:8000`
   - Set `COMMERCE_ENCRYPTION_KEY` for encrypted order/payment data at rest (Fernet key).  
     If omitted, a fallback key is derived from `SECRET_KEY` for development.
   - Optional Stripe Elements secure form:
     - `STRIPE_PUBLISHABLE_KEY=pk_test_...`
3) Start everything
```
docker-compose up --build
```
4) (Optional) Attach product images:
```
docker-compose exec -T backend python manage.py add_sample_images --use-real
```
   - Add `--replace` to replace existing images.

### Local (without Docker)
1) Create venv and install requirements:
```
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp envtemplate.txt .env
```
2) Update `.env` values.
3) Migrate and seed:
```
python manage.py migrate
python manage.py seed_catalog
python manage.py runserver
```
4) (Optional) Create admin user:
```
python manage.py createsuperuser
```
5) (Optional) Attach product images:
```
python manage.py add_sample_images --use-real
```
   - Add `--replace` to replace existing images.
6) (Optional) Create demo admin from env (quick testing):
```
DEMO_ADMIN_EMAIL=admin@example.com DEMO_ADMIN_PASSWORD=AdminPass123! \\
python manage.py create_demo_admin
```
7) (Optional) Cleanup expired access token blocks:
```
python manage.py cleanup_access_tokens
```

## Usage Guide
- API base: `http://localhost:8000/api`
- Demo page: `http://localhost:8000/`
- Note: the demo UI is served by Django at `http://localhost:8000/`.
- Focused testing pages:
  - `http://localhost:8000/cart/`
  - `http://localhost:8000/checkout/`
  - `http://localhost:8000/orders/`

Frontend structure:
- `index.html` is now a clean home dashboard with auth quick-actions and catalog browser.
- `cart.html`, `checkout.html`, and `orders.html` are dedicated flow pages for easier review/demo.
- Shared UI layer lives in:
  - `backend/static/ui.css`
  - `backend/static/ui.js`
  - `backend/static/home.js`
  - `backend/static/cart.js`
  - `backend/static/checkout.js`
  - `backend/static/orders.js`

### Auth
- Register (with CAPTCHA token): `POST /auth/register/`
- Login (2FA code optional): `POST /auth/login/`
  - 2FA is only required after a user enables it via `/auth/2fa/verify/`.
- Refresh (rotation enabled): `POST /auth/token/refresh/`
- Logout (blacklist refresh): `POST /auth/logout/`
- Logout all sessions: `POST /auth/logout-all/`
- Revoke access token: `POST /auth/token/revoke/`
- 2FA setup: `POST /auth/2fa/setup/`
- 2FA verify: `POST /auth/2fa/verify/`
- 2FA disable: `POST /auth/2fa/disable/`
 - Password reset request: `POST /auth/password/reset/`
 - Password reset confirm: `POST /auth/password/reset/confirm/`

Google OAuth:
- `POST /auth/oauth/google/`
  - Body: `{"access_token":"<google-access-token>"}`
- `POST /auth/oauth/google-code/`
  - Body: `{"code":"<oauth-code>","redirect_uri":"http://localhost:8000"}`
- (Optional) Allauth flow: `POST /auth/oauth/google-allauth/`

Password reset endpoints (dj-rest-auth):
- `POST /auth/password/reset/`
- `POST /auth/password/reset/confirm/`

### Catalog
- Product list: `GET /catalog/products/`
- Product detail: `GET /catalog/products/{id}/`
- Categories: `GET /catalog/categories/`
- Brands: `GET /catalog/brands/`
- Suggestions: `GET /catalog/suggest/?q=gpu`
 - Ordering: `ordering=relevance|price|-price|rating|name`
 - Upload image (admin only): `POST /catalog/products/{id}/images/`

Filtering and sorting:
- `GET /catalog/products/?min_price=100&max_price=500&brand=NexCore&category=graphics-cards&rating=4`
- `GET /catalog/products/?ordering=price` (or `-price`, `rating`, `name`)
Invalid filter values return `400`.

Image upload example (admin user required):
```
curl -X POST http://localhost:8000/api/catalog/products/1/images/ \
  -H "Authorization: Bearer <ADMIN_ACCESS_TOKEN>" \
  -F "image=@/path/to/image.png" \
  -F "alt_text=Front view"
```
When `DEBUG=1`, images are served under `http://localhost:8000/media/...`.
`backend/media` is gitignored and not part of the repo.
Upload rules: PNG/JPEG only, max 2MB, max 5 images per product, oversized images are resized.

### Commerce
- Cart:
  - `GET /commerce/cart/`
  - `POST /commerce/cart/items/`
  - `PATCH /commerce/cart/items/{item_id}/`
  - `DELETE /commerce/cart/items/{item_id}/`
- Guest carts use `X-Guest-Cart-Token`; logged-in users get persistent per-user carts.
- Checkout:
  - `GET /commerce/checkout/prefill/` (prefills known user info)
  - `GET /commerce/checkout/payment-config/` (returns Stripe publishable key for secure card element)
  - `GET /commerce/checkout/summary/`
  - `POST /commerce/checkout/place-order/`
- Order management:
  - `GET /commerce/orders/?status=&date_from=&date_to=`
  - `GET /commerce/orders/{order_id}/`
  - `POST /commerce/orders/{order_id}/cancel/`

Payment simulation behavior:
- Providers: `stripe_sandbox`, `paypal_sandbox`
- Example success card: `4242424242424242`
- If Stripe publishable key is configured, frontend can use Stripe secure Card Element and send tokenized `payment_token` instead of raw card fields.
- Failure scenarios:
  - `4000000000009995` → insufficient funds
  - `4000000000000002` → invalid card number
  - `4000000000000069` → expired card
  - `4000000000000127` → gateway timeout

Message queue flow:
- Payment events are published to `PaymentStatusMessage` queue table.
- Order state is updated by queue consumer logic (`pending_payment` → `payment_successful` / `payment_failed`).
- Failure or cancellation restores inventory to prevent stock drift.

Security and data handling:
- Raw card data is never persisted.
- Stored order/payment payloads (shipping address, payment metadata) are encrypted at rest.
- Checkout stock updates use transactional row locking to prevent overselling on concurrent payments.

## Task Specs
- Project 1 specification: `task.md`
- Project 2 specification: `task2.md`

## Notes for Review
- JWT access tokens are intended for in-memory storage on the client.
- Refresh token rotation is enabled and old tokens are blacklisted.
- Access tokens can be revoked via the denylist endpoint.
- Optional 2FA uses TOTP (Google Authenticator compatible).

## Search Implementation
- Product search uses DRF search filter on name/description/brand/category fields.
- Faceted filters use `django-filter` with strict validation for price, brand, and category.
- Suggestions are generated by simple name matching for quick feedback.

## Database + ACID Notes
- PostgreSQL provides ACID guarantees for transactional updates.
- Relational tables and foreign keys enforce product/category/brand integrity.
- Index-friendly filters (price, brand, category) support scalable queries.

## Architecture
- API-first Django monolith for Part 1 scope.
- Clean separation by app: `users` for auth, `catalog` for products.
 - Future-ready fields added (sku, slug, specs) for Parts 2–3.

## Compliance Notes
- No payment data stored in Part 1.
- JWT access tokens are short-lived and kept in memory only by the frontend.
- Password reset uses SMTP and avoids exposing user passwords.

## Student Can Explain
- JWT structure (header, payload, signature) and why access tokens are short-lived.
- Refresh token rotation and blacklist approach for token revocation.
- ACID properties and why PostgreSQL is suitable for relational product data.
- Scalability basics: DB indexing, filtering, and pagination with DRF.
- Architecture choice: Django monolith with API-first approach.

## Tests
From `backend/`:
```
python manage.py test
```
Docker:
```
docker-compose exec -T backend python manage.py test
```

## Test Coverage Map
- Auth: register/login, refresh rotation, logout, logout-all, access token revoke, 2FA validation.
- Catalog: list/detail, filters/sorting, search suggest, categories/brands, image upload permissions.
- Security: invalid filters, malformed inputs, and auth edge cases.

Manual checks (periodic):
- CAPTCHA verification during register (with a real token).
- Google OAuth login flow (client ID + redirect URI).
- 2FA setup + login with TOTP code.

## Reviewer Checklist
- Register user with CAPTCHA token.
- Login and refresh token (verify rotation).
- Enable 2FA, then login with code.
- Logout all sessions.
- Revoke access token.
- List products + filters + ordering.
- Upload a product image as admin.

## Final Review Checklist
- Docker up: `docker-compose up --build`
- Admin login works
- OAuth login works (Google)
- CAPTCHA is required for registration
- Tests pass: `docker exec -it i-love-shopping1_backend_1 python manage.py test -v 2`

## Runbook
- Start: `docker-compose up --build`
- Stop: `docker-compose down`
- View logs: `docker-compose logs -f backend`
- Cleanup token blocklist: `docker-compose exec backend python manage.py cleanup_access_tokens`
