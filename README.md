# Inventory Booking

Internal inventory and equipment booking system for small teams managing physical items, QR labels, locations, reservations, checkouts, returns, and item history.

## Stack

- PostgreSQL: source-of-truth database
- FastAPI: backend API and business rules
- SvelteKit: responsive web frontend / future PWA

## Repository Layout

- `backend/`: FastAPI application, tests, migrations later.
- `frontend/`: SvelteKit application.
- `docs/`: project notes, workflow docs, and task tracking.
- `docker-compose.yml`: local service topology for PostgreSQL, API, and web app.
- `inventory-booking-tool-proposal.md`: original product and architecture proposal.

## Prerequisites

- Python 3.13+
- `uv`
- Node.js 23+ and npm
- Docker Desktop or another Docker-compatible runtime for the full local stack

Docker is optional for editing and tests, but required for the PostgreSQL-backed integrated local environment.

## First-Time Setup

From the repository root:

```powershell
uv sync --directory .\backend
npm.cmd --prefix .\frontend install
```

Create local environment files:

```powershell
Copy-Item .\backend\.env.example .\backend\.env
Copy-Item .\frontend\.env.example .\frontend\.env
```

## Run Locally Without Docker

Backend:

```powershell
uv run --directory .\backend uvicorn inventory_booking_api.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
npm.cmd --prefix .\frontend run dev
```

The frontend defaults to `http://127.0.0.1:5173` and expects the API at `http://127.0.0.1:8000`.

## Run Full Stack With Docker

```powershell
docker compose up --build
```

Services:

- API: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:5173`
- PostgreSQL: `127.0.0.1:5432`

## Quality Checks

Backend:

```powershell
uv run --directory .\backend ruff check .
uv run --directory .\backend pytest
```

Frontend:

```powershell
npm.cmd --prefix .\frontend run check
npm.cmd --prefix .\frontend run lint
```

## Current Status

This repo is initialized as a clean starting point. The first backend endpoint is `GET /health`, and the first frontend page verifies that the app shell loads.

## Next Implementation Steps

1. Add PostgreSQL connection settings and Alembic migrations.
2. Define core database models for users, locations, items, QR codes, bookings, checkouts, returns, item events, and audit logs.
3. Implement availability/conflict tests before building checkout and return workflows.
