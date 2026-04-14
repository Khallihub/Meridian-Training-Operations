# Meridian Training Operations System

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
  docker compose up --build -d
  ```

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
  docker compose down -v
  ```

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

## Seeded Credentials

The default user is seeded in non-production mode (the compose setup uses development settings by default).

| Role | Username | Password | Notes |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `Admin@Meridian1` | Created at container startup when `APP_ENV != production`. |

No default learner/guest accounts are auto-seeded in this codebase.
