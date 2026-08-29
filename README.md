# Inventory Booking

Internal inventory and equipment booking system for small teams managing physical items, QR labels, locations, reservations, checkouts, returns, and item history.

## Stack

- PostgreSQL: source-of-truth database
- FastAPI: backend API and business rules
- SvelteKit: responsive web frontend / future PWA

## Repository Layout

- `backend/`: FastAPI application, tests, and Alembic migrations.
- `frontend/`: SvelteKit application.
- `frontend/src/lib/components/workspace/`: desktop workspace tab components.
- `docs/`: project notes, workflow docs, and task tracking.
- `docs/server-operations.md`: live server access, SSH identities, ownership, and AI-agent rules.
- `docs/development-and-deployment-workflow.md`: local, GitHub, and manual release workflow.
- `docs/production-runbook.md`: production deployment, health, backup, restore, and rollback.
- `docs/qr-scan-feature-plan.md`: implementation and rollout plan for authenticated phone QR routing.
- `docker-compose.yml`: base service topology for PostgreSQL, API, and web app. `docker-compose.override.yml` keeps local development ports, source mounts, and reload/dev-server commands.
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

The checked-in `docker-compose.override.yml` is applied automatically for local development. It exposes PostgreSQL, runs the backend with reload, and runs the frontend Vite dev server.

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

## Production

The application is live at `https://inventory.nica.network`. Production runs
the `main` branch from `/opt/docker/inventory` as a Docker Compose project behind
an Apache HTTPS reverse proxy.

Deployments are conscious manual actions; pushing to GitHub does not update the
server automatically. Start with:

- `docs/server-operations.md` for SSH access and server boundaries.
- `docs/development-and-deployment-workflow.md` for the release flow.
- `docs/production-runbook.md` for deployment, health checks, backups, and
  recovery.

## Quality Checks

Backend:

```powershell
uv run --directory .\backend ruff check .
uv run --directory .\backend pytest
```

PostgreSQL-only concurrency tests are skipped by default because they drop and recreate all tables
in the configured test database. Run them only against a disposable database:

```powershell
$env:POSTGRES_TEST_DATABASE_URL="postgresql+asyncpg://inventory:inventory@127.0.0.1:5432/inventory_booking_test"
uv run --directory .\backend pytest .\tests\test_postgres_concurrency.py
```

Frontend:

```powershell
npm.cmd --prefix .\frontend run check
npm.cmd --prefix .\frontend run lint
```

Regenerate frontend API schema types after backend schema changes:

```powershell
uv run --directory .\backend python .\scripts\generate_openapi.py | Out-File -FilePath .\frontend\src\lib\api\openapi.json -Encoding utf8
npm.cmd --prefix .\frontend run generate:api-types
```

## Current Status

This repo has working local and production Docker stacks. The production service
is live at `https://inventory.nica.network`. Backend health endpoints are
`GET /health` and `GET /health/database`. PostgreSQL migrations create users,
sessions, persons, locations, categories, tracked/stock asset definitions,
tracked units, stock batches, baskets, bookings, checkouts, returns, item
events, and audit logs.

The frontend is currently a desktop-first tabbed workspace:

- `Dashboard`: high-level counts.
- `Inventory`: assets, asset search, asset detail/history, basket entry, deletion, and asset state changes.
- `Locations`: spaces, stock by location, and movement workflows.
- `Persons`: team, user, and external contact records used for bookings and location responsibility.
- `Bookings`: filtered/sortable reservation list, editable booking details, check-out, and check-in workflows.
- `Stock`: availability heatmap for stock assets and tracked unique items, with cached range controls.
- `Basket`: temporary held items before confirming a booking.
- `Account`: login, logout, and editable current account name/email/password.
- `Admin`: users and categories.

The dedicated `/qr/<opaque-token>` route provides an authenticated, read-only,
phone-focused asset view. It preserves the scanned URL through login and can
open the resolved record in the full Inventory workspace.

Production operations are documented in `docs/server-operations.md` and
`docs/production-runbook.md`.

## API

Domain read and write endpoints require an authenticated session cookie from `POST /auth/login`.

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
- `PATCH /auth/me`
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
- `DELETE /locations/{location_id}`
- `GET /locations/images`
- `GET /locations/{location_id}/image`
- `GET /locations/{location_id}/image/content`
- `POST /locations/{location_id}/image`
- `DELETE /locations/{location_id}/image`
- `GET /persons`
- `POST /persons`
- `GET /persons/{person_id}`
- `PATCH /persons/{person_id}`
- `DELETE /persons/{person_id}`
- `GET /assets`
- `POST /assets`
- `GET /assets/{asset_id}`
- `PATCH /assets/{asset_id}`
- `DELETE /assets/{asset_id}`
- `GET /assets/images`
- `GET /assets/{asset_id}/image`
- `GET /assets/{asset_id}/qr`
- `POST /assets/{asset_id}/qr`
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
- `GET /bookings/availability/heatmap`
- `GET /bookings/availability/days`
- `GET /bookings/{booking_id}`
- `PATCH /bookings/{booking_id}`
- `DELETE /bookings/{booking_id}`
- `POST /bookings/{booking_id}/cancel`
- `GET /basket/active`
- `POST /basket`
- `PATCH /basket/{basket_id}`
- `POST /basket/{basket_id}/lines`
- `DELETE /basket/{basket_id}/lines/{line_id}`
- `POST /basket/{basket_id}/confirm`
- `POST /basket/{basket_id}/cancel`
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

1. Confirm automated daily database/upload backups, off-server retention, and
   restore-test ownership with Trebor.
2. Review, deploy, and physically verify the authenticated phone QR workflow in
   `docs/qr-scan-feature-plan.md`.
3. Collect production usage feedback and prioritize workflow corrections.
4. Add multi-line booking editing if real usage demonstrates the need.
