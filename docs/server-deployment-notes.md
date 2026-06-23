# Server Deployment Notes for IT Discussion

This document is a first-pass technical note for discussing whether the inventory booking tool can be hosted on an existing server. It is not a final production runbook yet.

Related short notes:

- `docs/it-server-request-note.md`: concise handoff note for IT.
- `docs/linux-server-access-basics.md`: Windows-to-Linux SSH basics for Marc.

## What The App Is

Internal web app for a small local team managing inventory, locations, reservations, checkouts, returns, and photos.

Current stack:

- Frontend: SvelteKit web app.
- Backend: FastAPI API.
- Database: PostgreSQL.
- Runtime: Docker Compose in local development.
- Uploaded photos: processed frontend-side first, then stored as files on the backend volume; metadata is stored in PostgreSQL.

## Target Hosting Shape

Recommended simple setup:

```text
Internet
  -> HTTPS subdomain
  -> reverse proxy
  -> Docker Compose app stack
       -> frontend container
       -> backend API container
       -> PostgreSQL container
       -> persistent volumes for database and uploads
```

Example public URL:

```text
https://inventar.nica.network
```

PostgreSQL should not be public. It should only be reachable from the app/backend on the server.

## What We Need To Ask IT

Can the server provide:

- A subdomain for the tool.
- HTTPS certificate handling for that subdomain.
- Docker and Docker Compose support.
- A reverse proxy route to the frontend/backend containers.
- Persistent server storage for PostgreSQL and uploads.
- Scheduled backups.
- Firewall rules so only HTTP/HTTPS are publicly exposed.

## Required Persistent Data

These must survive container rebuilds/restarts:

- PostgreSQL database data.
- Asset photo uploads.
- Location photo uploads.

Suggested server paths, if IT prefers explicit host mounts:

```text
/srv/inventory-booking/postgres
/srv/inventory-booking/uploads/assets
/srv/inventory-booking/uploads/locations
/srv/inventory-booking/backups
```

Exact paths can differ; the important part is that they are persistent and backed up.

## Production Environment Values

Production needs a separate environment configuration. Main values:

- `ENVIRONMENT=production`
- `SECRET_KEY=<strong random secret>`
- `DATABASE_URL=<internal postgres connection string>`
- `SESSION_COOKIE_SECURE=true`
- `CORS_ORIGINS=https://inventar.example.org`
- `ASSET_UPLOAD_DIR=<persistent asset upload path>`
- `LOCATION_UPLOAD_DIR=<persistent location upload path>`
- frontend `PUBLIC_API_BASE_URL=<public API base URL>`

The current local defaults are not production settings.

## Security Expectations

Minimum baseline:

- HTTPS only.
- Secure session cookies.
- Strong admin password.
- Database not exposed to the public internet.
- Only trusted users get accounts.
- Admin role controls user creation.
- Server firewall limits public access to `80`/`443`.
- Upload size limits at reverse proxy and backend.
- Regular OS/package/container updates.

This is an internal tool, not a public SaaS product, but it still contains operational data and photos, so basic production hygiene matters.

## Backups

Backups should include:

- PostgreSQL dump or volume snapshot.
- Uploaded photos directories/volumes.

Recommended backup frequency:

- weekly database backup.
- weekly upload backup, or file-system snapshot if available.
- Keep at least a few older restore points.

Important: a backup plan is only real if restore has been tested once.

## Deployment Steps Later

If IT confirms this hosting model is feasible, the next documentation/config tasks are:

1. Add `docker-compose.prod.yml`.
2. Add `.env.production.example`.
3. Document reverse proxy examples.
4. Document deployment commands.
5. Document migration command.
6. Document first-admin creation.
7. Add backup and restore scripts/docs.

## Open Questions For IT

- Which reverse proxy or server panel is used?
- Can Docker Compose services run long-term on this server?
- Where should persistent application data live?
- What backup mechanism already exists?
- Is there an existing monitoring/logging setup?
- Should the app live behind VPN/internal network, or is HTTPS + login enough?
- Should the backend and frontend share one subdomain, or should the API get a separate subdomain?
