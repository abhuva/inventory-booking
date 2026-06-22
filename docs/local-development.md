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

## Check Everything

```powershell
.\scripts\check.ps1
```
