# Production Deployment And Backup Runbook

This runbook is the operational baseline for deploying the inventory booking app beyond local development.

## Deployment Shape

```text
HTTPS reverse proxy
  -> frontend container, Node/SvelteKit on port 3000
  -> backend container, FastAPI on port 8000
  -> postgres container, private Docker network only
```

Do not expose PostgreSQL directly to the network in production.

## Required Environment

Set these values before using `docker-compose.prod.example.yml` as a production template:

```powershell
$env:POSTGRES_PASSWORD = "<strong-password>"
$env:DATABASE_URL = "postgresql+asyncpg://inventory:<strong-password>@postgres:5432/inventory_booking"
$env:CORS_ORIGINS = "https://inventory.example.org"
$env:PUBLIC_API_BASE_URL = "https://inventory.example.org"
$env:PUBLIC_APP_BASE_URL = "https://inventory.example.org"
$env:INTERNAL_API_TOKEN = "<random-long-token>"
```

Production startup now fails if local defaults are used with `APP_ENV=production`.

## First Deploy

1. Copy `docker-compose.prod.example.yml` to the server as the deployment compose file.
2. Set all required environment values through the server secret mechanism or an `.env` file with restricted permissions.
3. Start the stack.
4. Run Alembic migrations against the production database.
5. Seed the first admin account if needed.
6. Configure the reverse proxy for HTTPS and secure headers.
7. Confirm `SESSION_COOKIE_SECURE=true` and the public URL is HTTPS.

## Reverse Proxy Requirements

- Terminate TLS.
- Forward `Host`, `X-Forwarded-For`, and `X-Forwarded-Proto`.
- Route frontend traffic to port `3000`.
- Route API traffic to port `8000` if frontend and API share one hostname.
- Add HSTS after HTTPS is confirmed stable.
- Keep request body limits compatible with configured image upload limits.

## Backup Policy

Minimum baseline:

- [ ] Daily PostgreSQL dump.
- [ ] Off-server copy of each dump.
- [ ] Backup retention of at least 14 daily snapshots.
- [ ] Monthly restore test.
- [ ] Include upload volume backup with the database backup window.

Example logical dump from the server:

```powershell
docker compose exec -T postgres pg_dump -U inventory -d inventory_booking --format=custom > .\backups\inventory_booking_$(Get-Date -Format yyyyMMdd_HHmmss).dump
```

Example upload volume backup:

```powershell
docker run --rm -v inventory-booking_asset-uploads:/data -v ${PWD}\backups:/backup alpine tar czf /backup/asset_uploads_$(Get-Date -Format yyyyMMdd_HHmmss).tgz -C /data .
```

## Restore Test

Use a non-production environment.

1. Start a clean PostgreSQL container.
2. Restore the database dump.
3. Restore the upload archive into the upload volume.
4. Run migrations to confirm schema compatibility.
5. Start backend and frontend.
6. Verify login, inventory list, image retrieval, booking list, checkout list, and return list.

Example restore command:

```powershell
docker compose exec -T postgres pg_restore -U inventory -d inventory_booking --clean --if-exists .\backups\inventory_booking_latest.dump
```

## Deployment Checks

Run before promoting a build:

```powershell
uv run --directory .\backend ruff check .
uv run --directory .\backend pytest
npm.cmd --prefix .\frontend run check
npm.cmd --prefix .\frontend run lint
npm.cmd --prefix .\frontend run build
docker compose -f .\docker-compose.prod.example.yml config
```

## Rollback

- Keep the previous image tag available.
- Keep the latest pre-deploy database dump.
- If a migration is not safely reversible, restore the pre-deploy dump rather than attempting manual repair.
- Document every production restore with timestamp, operator, and reason.

