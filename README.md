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
Use `127.0.0.1` consistently instead of mixing it with `localhost`; the browser-readable CSRF cookie is host-scoped.

## Run Full Stack With Docker

```powershell
docker compose up --build
```

Apply database migrations after the containers are running:

```powershell
.\scripts\migrate.ps1
```

Seed the first admin account:

```powershell
$env:ADMIN_EMAIL = "admin@example.org"
$env:ADMIN_PASSWORD = "change-this-password"
$env:ADMIN_DISPLAY_NAME = "Admin"
.\scripts\seed-admin.ps1
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

This repo has a working Docker-backed local stack. Backend health endpoints are `GET /health` and `GET /health/database`. PostgreSQL migrations create users, sessions, locations, categories, tracked/stock assets, stock levels, item events, and audit logs.

## API

Read endpoints are open during early local development. Mutating endpoints require an authenticated session cookie from `POST /auth/login`.

Browser/session mutations also require CSRF protection:

```text
Cookie: inventory_booking_csrf=<token>
X-CSRF-Token: <same token>
```

Current endpoints:

- `GET /health`
- `GET /health/database`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`
- `GET /users`
- `POST /users`
- `GET /users/{user_id}`
- `PATCH /users/{user_id}`
- `GET /audit/logs`
- `GET /audit/item-events`
- `GET /categories`
- `POST /categories`
- `GET /categories/{category_id}`
- `PATCH /categories/{category_id}`
- `GET /locations`
- `POST /locations`
- `GET /locations/{location_id}`
- `PATCH /locations/{location_id}`
- `GET /assets`
- `POST /assets`
- `GET /assets/{asset_id}`
- `PATCH /assets/{asset_id}`
- `GET /stock-levels`
- `POST /stock-levels`
- `GET /stock-levels/{stock_level_id}`
- `PATCH /stock-levels/{stock_level_id}`
- `GET /bookings`
- `POST /bookings`
- `POST /bookings/availability`
- `GET /bookings/{booking_id}`
- `POST /bookings/{booking_id}/cancel`
- `GET /checkouts`
- `POST /checkouts`
- `GET /checkouts/{checkout_id}`

## Next Implementation Steps

1. Build return workflows on top of checkout lines.
2. Add checkout UI once return behavior is defined.
3. Add multi-line booking editing if real usage needs it.
