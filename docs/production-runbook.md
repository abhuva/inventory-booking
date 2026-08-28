# Production Runbook

This runbook covers deployment, health checks, backup, restore, and rollback for
the live service at `https://inventory.nica.network`.

For SSH identities, ownership boundaries, and AI-agent rules, read
`docs/server-operations.md` first.

## Live Deployment Shape

```text
Apache HTTPS reverse proxy
  -> 127.0.0.1:3000 -> frontend container
  -> 127.0.0.1:8000 -> backend container
  -> Docker network -> postgres container
```

The production project uses:

```text
Application directory: /opt/docker/inventory
Compose file:          docker-compose.prod.yml
Environment file:      .env
Git branch:            main
```

PostgreSQL has no public host port. The production `.env` is server-only and
must remain mode `600`.

## Deploy

Deploy only a validated commit already present on `origin/main`:

```bash
cd /opt/docker/inventory
bash scripts/deploy-production.sh
```

The script uses fast-forward-only Git updates, rebuilds the stack, runs Alembic
migrations, prints service status, and checks backend/database health. A push to
GitHub alone never triggers it.

Do not run the example Compose file in production. Trebor's live
`docker-compose.prod.yml` contains the loopback bindings required by Apache.

## Health And Logs

Public checks:

```powershell
curl.exe -I https://inventory.nica.network/
curl.exe https://inventory.nica.network/health
curl.exe https://inventory.nica.network/health/database
```

Server checks:

```bash
cd /opt/docker/inventory
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=100 backend
docker compose -f docker-compose.prod.yml logs --tail=100 frontend
docker compose -f docker-compose.prod.yml logs --tail=100 postgres
```

Healthy production currently means:

- the public page returns HTTP `200` over HTTPS;
- plain HTTP redirects to HTTPS;
- `/health` reports `environment: production`;
- `/health/database` reports `database: reachable`;
- all three containers are running and PostgreSQL is healthy.

## Backup Policy

Required baseline:

- daily PostgreSQL custom-format dump;
- upload-volume archive in the same backup window;
- off-server copy;
- at least 14 daily restore points;
- monthly restore test in a non-production environment;
- a recorded owner for monitoring backup failures.

Current status as of 2026-08-29: no app-level backup directory or user cron job
is visible to Marc. Confirm whether Trebor's server-wide backup system covers
both Docker volumes before treating this requirement as complete.

### Create A Manual Database Backup

On the server:

```bash
cd /opt/docker/inventory
mkdir -p backups
backup_stamp="$(date +%Y%m%d_%H%M%S)"
docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U inventory -d inventory_booking --format=custom \
  > "backups/inventory_booking_${backup_stamp}.dump"
```

### Create A Manual Upload Backup

Using the same `backup_stamp`:

```bash
docker run --rm \
  -v inventory_asset-uploads:/data:ro \
  -v /opt/docker/inventory/backups:/backup \
  alpine tar czf "/backup/asset_uploads_${backup_stamp}.tgz" -C /data .
```

Check that both files exist and are non-empty:

```bash
ls -lh "backups/inventory_booking_${backup_stamp}.dump" \
  "backups/asset_uploads_${backup_stamp}.tgz"
```

A copy under `/opt/docker/inventory/backups` protects against some application
mistakes but not server loss. Move or synchronize it to the agreed off-server
backup target.

## Restore Test

Never test restoration against the live production database or volumes.

In an isolated non-production Compose project:

1. Start a clean PostgreSQL container.
2. Restore the selected dump with `pg_restore`.
3. Restore the matching upload archive into a clean upload volume.
4. Run all Alembic migrations.
5. Start frontend and backend.
6. Verify login, inventory, photos, bookings, checkouts, returns, and audit
   history.
7. Record the date, backup filenames, result, and operator.

Example database input form for the isolated project:

```bash
docker compose -f docker-compose.restore.yml exec -T postgres \
  pg_restore -U inventory -d inventory_booking --clean --if-exists \
  < backups/inventory_booking_TIMESTAMP.dump
```

The exact restore Compose file and destination volumes must be reviewed before
running the command. A production restore is a destructive incident operation
and requires explicit approval plus a fresh snapshot of the current state.

## Rollback

Application rollback and database rollback are different:

- If no incompatible migration ran, deploy the previous known-good commit.
- If a migration changed data incompatibly, restoring code alone is not enough.
- Preserve a pre-deploy database dump for risky releases.
- Never run `alembic downgrade` in production without reviewing that specific
  migration's downgrade behavior.
- Record every production restore with timestamp, operator, reason, source
  backup, and verification result.

## Infrastructure Escalation

Contact Trebor for changes to Apache routing, TLS certificates, DNS, firewall,
root-owned Compose configuration, or server-wide backups. Marc and AI agents
should not attempt to work around those ownership boundaries.
