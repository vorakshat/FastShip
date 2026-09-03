# FastShip Backend

FastShip Backend is an asynchronous, high-performance RESTful logistics and parcel management API built with **FastAPI**, **SQLModel / SQLAlchemy**, and **PostgreSQL**. The service provides secure, role-based workflows for **Sellers** and **Delivery Partners**, automated shipment routing, real-time lifecycle tracking, Redis-backed JWT revocation, and Celery-powered background notification dispatch (Email & SMS).

---

## Tech Stack

- **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+)
- **Database & ORM:** [PostgreSQL](https://www.postgresql.org/), [SQLModel](https://sqlmodel.tiangolo.com/) / [SQLAlchemy](https://www.sqlalchemy.org/) (Async via `asyncpg`)
- **Schema Migrations:** [Alembic](https://alembic.sqlalchemy.org/)
- **Validation & Settings:** [Pydantic v2](https://docs.pydantic.dev/), [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- **Caching & Blacklisting:** [Redis](https://redis.io/) (`redis-py` async)
- **Task Queue & Workers:** [Celery](https://docs.celeryq.dev/) with Redis broker/result backend
- **Notifications:** [FastAPI-Mail](https://sabuhish.github.io/fastapi-mail/) (SMTP), [Twilio](https://www.twilio.com/) (SMS)
- **Server & Docs:** [Uvicorn](https://www.uvicorn.org/), Swagger UI, ReDoc, and [Scalar](https://github.com/scalar/scalar)

---

## Architecture & File Structure

```text
FastShip-Backend/
├── alembic.ini                   # Alembic configuration and migration environment settings
├── requirements.txt              # Production and development dependencies
├── migrations/                   # Alembic database migration scripts
│   ├── env.py                    # Async migration engine bootstrap and metadata registration
│   └── versions/                 # Revision history files (initial schema, M2M links, cascade triggers)
└── app/                          # Core application package
    ├── main.py                   # FastAPI app factory, lifespan hooks, and router mounting
    ├── config.py                 # Pydantic BaseSettings for DB, Redis, JWT, Mail, and Twilio
    ├── utils.py                  # JWT encoding/decoding, password hashing, template helpers
    ├── api/                      # Presentation layer / HTTP transport
    │   ├── router.py             # Master APIRouter aggregating all domain sub-routers
    │   ├── dependencies.py       # Dependency injection (sessions, services, auth/role guards)
    │   ├── routers/              # Controller endpoints partitioned by domain
    │   │   ├── delivery_partner.py  # Partner registration, JWT login, profile update, logout
    │   │   ├── seller.py            # Seller registration, login, email verification, password reset
    │   │   └── shipment.py          # Shipment CRUD, tag association, tracking, cancelling, reviews
    │   └── schemas/              # Pydantic DTOs for request input validation and response shaping
    │       ├── delivery_partner.py
    │       ├── seller.py
    │       └── shipment.py
    ├── core/                     # Cross-cutting foundational modules
    │   ├── exceptions.py         # Custom FastShipError hierarchy and centralized exception handlers
    │   └── security.py           # OAuth2PasswordBearer schemes for distinct actor roles
    ├── database/                 # Persistence layer
    │   ├── models.py             # SQLModel tables (Shipment, Seller, DeliveryPartner, Tag, Order, Review)
    │   ├── session.py            # Async engine configuration and AsyncSession generator
    │   └── redis.py              # Redis client for token revocation (JTI blacklist) and OTP codes
    ├── services/                 # Business logic and transaction orchestration layer
    │   ├── base.py               # Generic CRUD service base class
    │   ├── delivery_partner.py   # Partner capacity checks and route matching
    │   ├── notification.py       # Async mail and SMS event triggers
    │   ├── seller.py             # Seller account lifecycle and credential resets
    │   ├── shipment.py           # Shipment booking, partner assignment, status transitions
    │   ├── shipment_event.py     # Shipment history timeline updates
    │   └── user.py               # Base user credential validation and token generation
    ├── templates/                # Jinja2 HTML templates for tracking pages and email verification
    └── worker/                   # Asynchronous background job processing
        ├── main.py               # Standalone worker diagnostic app
        └── tasks.py              # Celery tasks (asynchronous transactional email, SMS via Twilio)
```

---

## Key Features

- **Relational Data Modeling & M2M Associations:**
  - Built on SQLModel/SQLAlchemy with strict foreign key constraints.
  - Many-to-Many relationships configured via dedicated join tables:
    - `ShipmentTag` linking `Shipment` and `Tag` models with immediate loading.
    - `Order` linking `Shipment` and `Product` models.
  - One-to-Many audit history via `ShipmentEvent` configured with `cascade="all, delete-orphan"`.
- **Role-Based Authentication & Redis Token Revocation:**
  - Independent OAuth2 password bearer schemes for `Seller` (`/seller/token`) and `DeliveryPartner` (`/partner/token`).
  - JWT tokens embed standard claims and unique `jti` identifiers.
  - Logging out immediately adds the token's `jti` to an async Redis blacklist, preventing replay attacks prior to token expiration.
- **Centralized Exception Handling:**
  - Standardized custom exception tree in `app/core/exceptions.py` derived from `FastShipError`.
  - Automatic status mapping (`EntityNotFound` $\rightarrow$ 404, `ClientNotAuthorized` $\rightarrow$ 401, `DeliveryPartnerCapacityExceeded` $\rightarrow$ 406).
  - Centralized registration dynamic hook returning consistent JSON error payloads.
- **Asynchronous Task Processing (Celery + Redis):**
  - Decoupled, non-blocking notification pipeline for heavy operations.
  - Background HTML email delivery via `FastMail` and SMS dispatch via `Twilio` with built-in retry backoff policies (`max_retries=3`, `default_retry_delay=60`).
- **Real-Time Parcel Tracking & Web Views:**
  - Server-side rendered Jinja2 tracking views (`/shipment/track`) presenting chronological status events (`placed`, `in_transit`, `out_for_delivery`, `delivered`, `cancelled`).

---

## Getting Started / Local Setup

### Prerequisites

- **Python:** 3.10 or higher
- **PostgreSQL:** Running instance (local or containerized)
- **Redis:** Running instance on port `6379`

### 1. Clone the Repository

```bash
git clone https://github.com/akshatVora-hub/FastShip.git
cd FastShip
```

### 2. Create and Activate Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux (Bash/Zsh):**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Application Settings
APP_NAME=FastShip
APP_DOMAIN=localhost:8000

# PostgreSQL Database
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_postgres_password
POSTGRES_DB=fastship_db

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Security & JWT
JWT_SECRET=your_super_secret_jwt_key_here
JWT_ALGORITHM=HS256

# Mail Configuration (SMTP)
MAIL_USERNAME=your_email@example.com
MAIL_PASSWORD=your_app_password
MAIL_FROM=no-reply@fastship.com
MAIL_FROM_NAME=FastShip
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_STARTTLS=True
MAIL_SSL_TLS=False
USE_CREDENTIALS=True
VALIDATE_CERTS=True

# Twilio SMS Credentials
TWILIO_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_NUMBER=+1234567890
```

### 5. Run Database Migrations

Apply the existing Alembic migration revisions to synchronize your database schema:

```bash
alembic upgrade head
```

### 6. Start the Services

**Run the API Server (Uvicorn):**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Run the Background Worker (Celery) in a separate terminal:**
```bash
celery -A app.worker.tasks.app worker --loglevel=info
```

---

## API Reference & Documentation

Once the server is running, explore and test the endpoints using interactive API documentations:

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Scalar UI:** [http://localhost:8000/scalar](http://localhost:8000/scalar)

### Endpoint Summary

| HTTP Method | Route Path | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| **Delivery Partner** | | | |
| `POST` | `/partner/signup` | Register a new delivery partner | **No** |
| `POST` | `/partner/token` | Authenticate partner and issue JWT bearer token | **No** |
| `GET` | `/partner/verify` | Confirm and verify delivery partner email address | **No** |
| `POST` | `/partner/` | Update authenticated delivery partner profile details | **Yes** (Partner) |
| `GET` | `/partner/logout` | Revoke session and add token JTI to Redis blacklist | **Yes** (Partner) |
| **Seller** | | | |
| `POST` | `/seller/signup` | Register a new merchant/seller account | **No** |
| `POST` | `/seller/token` | Authenticate seller and issue JWT bearer token | **No** |
| `GET` | `/seller/verify` | Confirm and verify seller email address | **No** |
| `POST` | `/seller/forgot_password` | Dispatch password reset link to user's registered email | **No** |
| `GET` | `/seller/reset_password_form` | Serve HTML password reset web form | **No** |
| `POST` | `/seller/reset_password` | Update user password using validated reset token | **No** |
| `GET` | `/seller/logout` | Revoke session and add token JTI to Redis blacklist | **Yes** (Seller) |
| **Shipment** | | | |
| `GET` | `/shipment/` | Fetch full details of a shipment by UUID | **Yes** (Seller) |
| `POST` | `/shipment/` | Create a new parcel shipment and auto-assign delivery partner | **Yes** (Seller) |
| `PATCH` | `/shipment/` | Update shipment payload / status event | **Yes** (Partner) |
| `GET` | `/shipment/cancel` | Cancel an active shipment | **Yes** (Seller) |
| `DELETE` | `/shipment/` | Permanently delete a shipment record by ID | **No** |
| `GET` | `/shipment/track` | Render public HTML shipment status & tracking timeline | **No** |
| `GET` | `/shipment/tagged` | Retrieve all shipments filtered by tag category | **No** |
| `GET` | `/shipment/tag` | Attach a classification tag to a shipment | **No** |
| `DELETE` | `/shipment/remove_tag` | Detach a tag from a shipment | **No** |
| `GET` | `/shipment/review` | Serve HTML review submission page | **No** |
| `POST` | `/shipment/review` | Submit rating (1-5) and feedback for delivered parcel | **No** |

---

## Database & Migrations

Database schema changes are tracked and versioned using **Alembic**. The configuration in `migrations/env.py` dynamically loads the connection string from `app.config.database_settings` and binds to `SQLModel.metadata`.

- **Apply all migrations:**
  ```bash
  alembic upgrade head
  ```

- **Generate a new migration after modifying models:**
  ```bash
  alembic revision --autogenerate -m "describe_your_schema_change"
  ```

- **Roll back the last applied migration:**
  ```bash
  alembic downgrade -1
  ```

- **Inspect current migration head:**
  ```bash
  alembic current
  ```
