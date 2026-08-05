# Development And Deployment Workflow

This document explains how to keep local development, GitHub, server
deployment, and production data separated.

## Recommended Shape

Use this workflow for normal changes:

```text
local development
  -> local checks
  -> git commit
  -> push to GitHub
  -> server pulls latest code
  -> server rebuilds containers
  -> server runs database migrations
  -> app restarts
```

The server should run a known committed version of the app. Avoid long-term
deployments by copying arbitrary local working directories to the server.
Copying can be useful for an early prototype, but Git-based deployment is
safer and easier to reason about.

## Why GitHub Helps

GitHub is useful even if the server can technically run without it:

- It provides a clean source of truth for the code.
- It records what changed and when.
- It makes rollback to an older version possible.
- It avoids missing files during deployment.
- It makes server updates repeatable with `git pull`.
- It helps separate committed app code from local experiments.

Secrets and production environment files must not be committed to GitHub.

## Local Development

Develop against a local database and local containers. The local database is
disposable and can be reset, seeded with fake data, and used for migration
testing.

Typical local workflow:

```powershell
docker compose up --build
.\scripts\migrate.ps1
```

Backend checks:

```powershell
uv run --directory .\backend ruff check .
uv run --directory .\backend pytest
```

Frontend checks:

```powershell
npm.cmd --prefix .\frontend run check
npm.cmd --prefix .\frontend run lint
```

Environment/deployment config check:

```powershell
docker compose config
```

## Production Server

The production server should have a stable checkout under:

```text
/opt/docker/inventory
```

The production `.env` file lives only on the server:

```text
/opt/docker/inventory/.env
```

It contains production database credentials, public URLs, and internal tokens.
Keep it out of Git and restrict permissions.

Recommended permissions:

```bash
chmod 600 /opt/docker/inventory/.env
```

The server-local Compose file is:

```text
/opt/docker/inventory/inventory-compose.yml
```

It is copied from `docker-compose.prod.example.yml` and intentionally not
tracked in Git. This allows the server to keep small local deployment details
without committing secrets or server-only configuration.

## Convert Prototype Copy To Git Checkout

The first prototype deployment was copied from a local working directory. To
turn that directory into a Git-backed checkout while keeping the server `.env`:

```bash
cd /opt/docker/inventory
git init
git remote add origin https://github.com/abhuva/inventory-booking.git
git fetch origin main
git checkout -B main origin/main
cp docker-compose.prod.example.yml inventory-compose.yml
chmod 600 .env
```

After conversion, confirm the checkout and ignored server files:

```bash
git status --short --branch
git check-ignore -v .env inventory-compose.yml
```

## Server Update Flow

After GitHub is set up and the server directory is a Git checkout, a typical
server update is:

```bash
cd /opt/docker/inventory
git pull
docker compose -f inventory-compose.yml up -d --build
docker compose -f inventory-compose.yml exec -T backend \
  uv run alembic upgrade head
```

The same flow is available as a manual deployment script:

```bash
cd /opt/docker/inventory
bash scripts/deploy-production.sh
```

The script intentionally does not run automatically. Production updates should
be a conscious manual action.

Then check the running services:

```bash
docker compose -f inventory-compose.yml ps
docker compose -f inventory-compose.yml logs --tail=100 backend
docker compose -f inventory-compose.yml logs --tail=100 frontend
```

Check backend health from inside the server:

```bash
docker compose -f inventory-compose.yml exec -T backend \
  curl http://127.0.0.1:8000/health
docker compose -f inventory-compose.yml exec -T backend \
  curl http://127.0.0.1:8000/health/database
```

## Local Database Vs Production Database

Keep local and production data separate.

The local database is for development:

- disposable data
- fake test data
- resettable schema
- migration experiments
- automated tests

The production database is real operational data:

- do not reset casually
- do not manually edit unless necessary
- change schema only through Alembic migrations
- change business data through the app UI, API, or reviewed admin scripts
- back up before risky changes

## Backups

Production backups must include:

- PostgreSQL database data
- uploaded asset and location photos

The database is the source of truth for operational state. Uploaded photos live
in the Docker upload volume.

Create a database backup:

```bash
cd /opt/docker/inventory
mkdir -p backups

docker compose -f inventory-compose.yml exec -T postgres \
  pg_dump -U inventory -d inventory_booking --format=custom \
  > backups/inventory_booking_$(date +%Y%m%d_%H%M%S).dump
```

Create an upload volume backup:

```bash
docker run --rm \
  -v inventory_asset-uploads:/data \
  -v /opt/docker/inventory/backups:/backup \
  alpine tar czf /backup/asset_uploads_$(date +%Y%m%d_%H%M%S).tgz \
  -C /data .
```

Backups stored only on the same server are not enough. Arrange an off-server
copy with IT or another backup target.

## Restore Principle

A backup plan is only reliable after a restore has been tested.

Restore tests should happen in a non-production environment:

1. Start a clean database.
2. Restore the latest database dump.
3. Restore the upload archive.
4. Run migrations.
5. Start backend and frontend.
6. Verify login, inventory, bookings, checkout/return history, and image loading.

## Current Prototype Note

The first server deployment was copied from the local working directory to get
the prototype running quickly. That is acceptable for the first deployment, but
future updates should move to a GitHub-backed deployment flow.
