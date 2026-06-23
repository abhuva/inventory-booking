# Inventory Booking

Internal inventory and equipment booking system for small teams managing physical items, QR labels, locations, reservations, checkouts, returns, and item history.

## Stack

- PostgreSQL: source-of-truth database
- FastAPI: backend API and business rules
- SvelteKit: responsive web frontend / future PWA

## Repository Layout

- `backend/`: FastAPI application, tests, migrations later.
- `frontend/`: SvelteKit application.
- `frontend/src/lib/components/workspace/`: desktop workspace tab components.
- `docs/`: project notes, workflow docs, and task tracking.
- `docs/server-deployment-notes.md`: first-pass notes for discussing server hosting with IT.
- `docker-compose.yml`: local service topology for PostgreSQL, API, and web app.
- upload Docker volumes: processed asset/location photos stored outside Postgres.
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

Asset and location photos are stored as processed derivatives only. The frontend crops/resizes/compresses camera or file input before upload, and the backend stores the result in Docker upload volumes while keeping metadata in PostgreSQL.

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

The frontend is currently a desktop-first tabbed workspace:

- `Dashboard`: high-level counts.
- `Inventory`: assets, asset search, asset detail/history, and asset state changes.
- `Locations`: spaces, stock by location, and movement workflows.
- `Stock`: stock availability heatmap.
- `Bookings`: reservation list, booking details, check-out, and check-in workflows.
- `Field / QR`: QR label creation, assignment, and lookup.
- `Admin`: users and categories.

For initial server hosting discussion, see `docs/server-deployment-notes.md`.

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
- `GET /assets/images`
- `GET /assets/{asset_id}/image`
- `GET /assets/{asset_id}/image/content`
- `POST /assets/{asset_id}/image`
- `DELETE /assets/{asset_id}/image`
- `POST /assets/{asset_id}/transfer`
- `POST /assets/{asset_id}/maintenance/start`
- `POST /assets/{asset_id}/maintenance/complete`
- `POST /assets/{asset_id}/state`
- `GET /stock-levels`
- `POST /stock-levels`
- `POST /stock-levels/transfer`
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
- `GET /returns`
- `POST /returns`
- `GET /returns/{return_id}`
- `GET /qr-codes`
- `POST /qr-codes`
- `GET /qr-codes/{token}/resolve`
- `POST /qr-codes/{token}/assign`

## Next Implementation Steps

1. Add multi-line booking editing if real usage needs it.
2. Turn `docs/server-deployment-notes.md` into a production deployment runbook after IT confirms the server setup.
3. Add backup and restore documentation.
