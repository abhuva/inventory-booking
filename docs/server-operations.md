# Production Server Operations

This is the source of truth for accessing and operating the live inventory
booking server. It was verified against the running system on 2026-08-28 UTC.

## Current Production State

- Public URL: `https://inventory.nica.network`
- Server SSH host: `nica.network`
- Server SSH user: `Marc`
- Application directory: `/opt/docker/inventory`
- GitHub repository: `git@github.com:abhuva/inventory-booking.git`
- Deployed branch: `main`
- Production Compose file: `/opt/docker/inventory/docker-compose.prod.yml`
- Production environment file: `/opt/docker/inventory/.env`
- Public reverse proxy: Apache, managed by Trebor

HTTP redirects to HTTPS. Apache forwards requests to containers bound only to
the server loopback interface:

```text
https://inventory.nica.network
  -> Apache reverse proxy and TLS
  -> 127.0.0.1:3000  SvelteKit frontend
  -> 127.0.0.1:8000  FastAPI backend routes
  -> Docker-private PostgreSQL service
```

The running containers are:

```text
inventory-frontend-1
inventory-backend-1
inventory-postgres-1
```

Persistent data is stored in Docker volumes:

```text
inventory_postgres-data
inventory_asset-uploads
```

## Connect From Windows

The private SSH key stays on Marc's Windows computer and must never be added to
Git:

```text
C:\Users\Marc Bielert\.ssh\inventory_nica_ed25519
```

Connect from PowerShell:

```powershell
ssh -i "$env:USERPROFILE\.ssh\inventory_nica_ed25519" Marc@nica.network
```

Run one server command without opening an interactive shell:

```powershell
$serverKey = "$env:USERPROFILE\.ssh\inventory_nica_ed25519"
$remoteCommand = @"
cd /opt/docker/inventory
docker compose -f docker-compose.prod.yml ps
"@
ssh -i $serverKey Marc@nica.network $remoteCommand
```

When the prompt changes to `Marc@nica`, commands run on the Linux server. Use
`exit` to return to PowerShell.

## SSH And GitHub Key Roles

There are two separate SSH identities:

1. The Windows key `inventory_nica_ed25519` authenticates Marc or a local AI
   agent to `nica.network`.
2. The server key `~/.ssh/inventory_booking_github_ed25519` authenticates the
   server to GitHub as a read-only repository deploy key.

The server's `~/.ssh/config` selects the deploy key for `github.com`. This lets
the server pull committed code without storing Marc's personal GitHub
credentials. The deploy key cannot push to GitHub.

Never copy either private key into the repository, chat, logs, or documentation.

## Safe Inspection Commands

After connecting to the server:

```bash
cd /opt/docker/inventory
git status --short --branch
git log -1 --oneline
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=100 backend
docker compose -f docker-compose.prod.yml logs --tail=100 frontend
```

Public checks from Windows:

```powershell
curl.exe -I https://inventory.nica.network/
curl.exe https://inventory.nica.network/health
curl.exe https://inventory.nica.network/health/database
```

Expected health responses report `environment` as `production` and the database
as `reachable`.

Do not print `/opt/docker/inventory/.env`. It contains production credentials
and tokens. It should remain server-only with mode `600`.

## AI-Agent Operating Rules

An AI agent working from this repository should:

1. Read `AGENTS.md`, `README.md`, `ARCHITECTURE.md`, and this document first.
2. Inspect `git status` before changing files and preserve unrelated user work.
3. Use the Windows SSH identity shown above for server access.
4. Treat server inspection as read-only unless Marc explicitly requests a
   deployment or other production change.
5. Never display, download, replace, or commit the production `.env` or private
   SSH keys.
6. Never edit application source directly on the server. Change it locally on
   a feature branch, validate it, commit it, and deploy a commit from `main`.
7. Do not change Apache, TLS, DNS, firewall, or root-owned files. Coordinate
   those changes with Trebor.
8. Before a deployment, confirm that the intended commit is on `origin/main`
   and that the production checkout has no unexpected tracked changes.
9. After a deployment, check container status, both health endpoints, and the
   public HTTPS page.

Read-only server checks do not alter production. Commands such as `git pull`,
`docker compose up`, migrations, restores, database writes, container restarts,
and edits under `/opt/docker/inventory` are production changes.

## File Ownership Boundary

- Marc owns the application checkout and `.env`.
- Trebor created the root-owned `docker-compose.prod.yml` that exposes the
  frontend and backend only on `127.0.0.1` for Apache.
- Trebor owns the Apache virtual host, TLS certificate, DNS, and server-wide
  infrastructure.

Do not replace `docker-compose.prod.yml` with
`docker-compose.prod.example.yml`: the example intentionally has no host port
bindings and would disconnect Apache from the app.

## Known Operational Gap

No app-level backup directory or user cron job was visible under Marc's account
during the 2026-08-28 UTC audit. Trebor may have server-wide backups that Marc
cannot inspect.
Confirm the database/upload backup schedule, retention, off-server destination,
and restore-test ownership before relying on the app for irreplaceable data.

See `docs/production-runbook.md` for deployments, backups, restores, and
incident checks.
