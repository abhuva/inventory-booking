# Development And Deployment Workflow

Local development, GitHub, and production have separate responsibilities and
data. Production deployment is manual by design.

## Normal Change Flow

```text
feature branch on Marc's computer
  -> local checks
  -> commit and push to GitHub
  -> review and integrate into main
  -> conscious manual deployment
  -> server pulls origin/main
  -> containers rebuild and restart
  -> Alembic migrations run
  -> health checks run
```

Pushing to GitHub does not update production. The server has no webhook, polling
job, or automatic deployment. This keeps the decision to release separate from
the decision to publish source code.

## Repository Roles

- Local checkout: development, tests, and feature branches.
- GitHub: shared source of truth and history.
- Production checkout: a clean checkout of `main`, used only to run the app.
- PostgreSQL: source of truth for operational inventory and booking data.
- Docker upload volume: persistent asset and location photos.

Secrets, private keys, production `.env` files, and server-local Compose files
must never be committed to GitHub.

## Local Development

Start the local stack and apply migrations:

```powershell
docker compose up --build
.\scripts\migrate.ps1
```

Run the standard checks:

```powershell
.\scripts\check.ps1
docker compose config
```

The local database is disposable. Use fake data, migration experiments, and
automated tests locally. Do not connect development tools to the production
database by default.

## Git Workflow

Create a branch for each scoped change:

```powershell
git switch main
git pull --ff-only origin main
git switch -c feature/short-description
```

After validation, commit and push the feature branch. Integrate reviewed work
into `main` before deployment. Do not deploy an uncommitted local directory or
copy source files manually to the server.

## Production Layout

The current server layout is:

```text
/opt/docker/inventory/                     Git checkout of origin/main
/opt/docker/inventory/.env                 server-only secrets, mode 600
/opt/docker/inventory/docker-compose.prod.yml
                                            root-owned live Compose file
```

The server pulls GitHub through a read-only deploy key. It cannot push changes
back to GitHub.

See `docs/server-operations.md` for SSH access and the full production map.

## Manual Deployment

Before deploying:

1. Run the local quality checks appropriate to the change.
2. Confirm the intended commit is present on `origin/main`.
3. Check that production is healthy.
4. Create or confirm a recent backup before risky schema or data changes.

Connect to the server and run:

```bash
cd /opt/docker/inventory
bash scripts/deploy-production.sh
```

Or invoke it directly from Windows PowerShell:

```powershell
$serverKey = "$env:USERPROFILE\.ssh\inventory_nica_ed25519"
$deployCommand = "cd /opt/docker/inventory && bash scripts/deploy-production.sh"
ssh -i $serverKey Marc@nica.network $deployCommand
```

The script:

1. fetches and fast-forwards to `origin/main`;
2. validates the server `.env` and `docker-compose.prod.yml`;
3. rebuilds and starts the containers;
4. applies Alembic migrations;
5. prints container status;
6. checks the API and database health endpoints from inside Docker.

It intentionally does not run automatically.

## Post-Deploy Checks

On the server:

```bash
cd /opt/docker/inventory
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=100 backend
docker compose -f docker-compose.prod.yml logs --tail=100 frontend
```

From Windows:

```powershell
curl.exe -I https://inventory.nica.network/
curl.exe https://inventory.nica.network/health
curl.exe https://inventory.nica.network/health/database
```

Also log in through the browser and smoke-test the workflow affected by the
release.

## Production Data Rules

Production data is real operational data:

- do not reset it for testing;
- apply schema changes only through Alembic migrations;
- prefer the app UI or reviewed scripts over manual SQL writes;
- take a backup before risky migrations or bulk corrections;
- test restores outside production.

For backup, restore, rollback, and incident commands, use
`docs/production-runbook.md`.
