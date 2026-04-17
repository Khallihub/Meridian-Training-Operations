# Meridian Training Operations System

**Project type:** Fullstack (Backend + Frontend)

A full-stack training operations platform for managing courses, sessions, bookings, attendance, replay access, checkout/payments, and operational monitoring. The stack is container-first and designed to run locally with Docker Compose.

## Architecture & Tech Stack

* **Frontend:** Vue 3, TypeScript, Vite, TailwindCSS, Pinia, Vue Router
* **Backend:** Python 3.11, FastAPI, SQLAlchemy (async), Alembic, Celery
* **Database:** PostgreSQL 15
* **Containerization:** Docker & Docker Compose (Required)

## Project Structure

*Below is this repository's structure (trimmed to key paths)*

```text
.
├── backend/                    # FastAPI app, Alembic migrations, backend Dockerfile
│   ├── app/
│   ├── alembic/
│   ├── tests/
│   └── .env.example            # Example backend environment variables
├── frontend/                   # Vue SPA and frontend Dockerfile
├── monitoring/                 # Prometheus/Grafana config
├── nginx/                      # Reverse-proxy config and Dockerfile
├── docker-compose.yml          # Multi-container orchestration - MANDATORY
├── run_tests.sh                # Standardized test execution script - MANDATORY
└── README.md                   # Project documentation - MANDATORY
```

## Prerequisites

To ensure a consistent environment, this project is designed to run within containers. You must have the following installed:
* [Docker](https://docs.docker.com/get-docker/)
* [Docker Compose](https://docs.docker.com/compose/install/)

## Running the Application

1. **Build and Start Containers:**
  ```bash
  docker-compose up --build -d
  ```
  > **Note:** Both `docker-compose` and `docker compose` (plugin form) are supported. Use whichever is available on your system.

2. **Environment File (Optional Local Override):**
  If you want backend environment overrides, copy the example env file:
  ```bash
  cp backend/.env.example backend/.env
  ```

3. **Access the App:**
  * Frontend: `http://localhost`
  * Backend API: `http://localhost/api/v1`
  * API Documentation: `http://localhost/api/v1/docs`
  * ReDoc: `http://localhost/api/v1/redoc`
  * Prometheus: `http://localhost:19090`
  * Grafana: `http://localhost:3000`

4. **Stop the Application:**
  ```bash
  docker-compose down -v
  ```

## Verification

After starting the application, verify it is running correctly:

### Backend API Verification

```bash
# Health check — should return {"status": "ok", ...}
curl http://localhost/api/v1/monitoring/health

# Login as admin — should return access_token and refresh_token
curl -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "Admin@Meridian1"}'

# Use the access_token from above to list courses
curl http://localhost/api/v1/courses \
  -H "Authorization: Bearer <access_token>"
```

### Frontend Verification

1. Open `http://localhost` in a browser.
2. Log in with Admin credentials: username `admin`, password `Admin@Meridian1`.
3. Verify the dashboard loads and the navigation sidebar appears.
4. Navigate to **Sessions** and confirm the calendar view renders.

## Testing

All unit/integration tests for backend and frontend are executed via a single standardized script.

Run:

```bash
chmod +x run_tests.sh
./run_tests.sh
```

Useful options:

```bash
./run_tests.sh --backend
./run_tests.sh --frontend
./run_tests.sh -k test_booking
```

`run_tests.sh` returns standard exit codes (`0` for success, non-zero for failure), making it CI/CD friendly.

Expected result: all tests pass with exit code 0.

### End-to-End Browser Tests

Browser-level E2E tests (Playwright) are located in `frontend/e2e/`. These are executed inside CI containers and do not require any local installation. See `frontend/playwright.config.ts` for configuration.

## Seeded Credentials

The following demo users are seeded in non-production mode (the compose setup uses `APP_ENV=development` by default). All users are created at container startup.

| Role | Username | Password | Notes |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `Admin@Meridian1` | Full system access. Created by docker-entrypoint.sh. |
| **Instructor** | `instructor` | `Instructor@Meridian1` | Can manage sessions, attendance, and replays for assigned sessions. |
| **Learner** | `learner` | `Learner@Meridian1` | Can browse, book sessions, view replays, and manage own profile. |
| **Finance** | `finance` | `Finance@Meridian1` | Payment processing, refunds, and reconciliation. |
| **DataOps** | `dataops` | `DataOps@Meridian1` | Ingestion source management, job monitoring, and alerts. |

### Roles Overview

- **admin** — Full access to all endpoints and administrative operations.
- **instructor** — Manage sessions they are assigned to, take attendance, upload replays.
- **learner** — Book sessions, attend classes, view replays, manage bookings.
- **finance** — View and manage payments, process refunds, generate reconciliation exports.
- **dataops** — Manage ingestion sources, monitor background jobs, view system alerts.
