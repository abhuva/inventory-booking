# Local Development

## One-Time Setup

```powershell
.\scripts\setup.ps1
```

This installs backend and frontend dependencies and creates local `.env` files when missing.

## Start Services Manually

Backend:

```powershell
uv run --directory .\backend uvicorn inventory_booking_api.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
npm.cmd --prefix .\frontend run dev
```

## Full Stack

```powershell
docker compose up --build
```

Docker is required for PostgreSQL until a separate local PostgreSQL instance is configured.

After the containers are running, apply migrations:

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

If Docker Desktop is running but `docker` is not recognized in PowerShell, open a new terminal first.
If it is still unavailable, use Docker Desktop's bundled CLI directly:

```powershell
& 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' compose up --build
```

Useful Docker commands:

```powershell
docker compose ps
docker compose logs --tail=120 backend
docker compose down
```

Do not use `docker compose down -v` unless you intentionally want to delete the local PostgreSQL data volume.

## Database Inspection

PostgreSQL does not open in a browser. Use `psql` or a database client.

```powershell
docker compose exec postgres psql -U inventory -d inventory_booking
```

Useful `psql` commands:

```sql
\dt
\d assets
\q
```

## Check Everything

```powershell
.\scripts\check.ps1
```
