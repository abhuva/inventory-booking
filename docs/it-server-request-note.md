# IT Server Request Note

We would like to host a small internal inventory booking web app on our server.

## App Summary

- Internal tool for a small team.
- Manages inventory, locations, bookings, check-outs/check-ins, QR labels, and photos.
- Stack:
  - SvelteKit frontend
  - FastAPI backend
  - PostgreSQL database
  - Docker Compose runtime

## What We Need From The Server

- Subdomain, likely `inventar.nica.network`.
- HTTPS for that subdomain.
- Docker and Docker Compose available.
- Reverse proxy routing to the app containers.
- Persistent storage for:
  - PostgreSQL data
  - uploaded asset photos
  - uploaded location photos
- Backups for database and uploads.
- PostgreSQL not exposed publicly.
- Public access only via HTTPS.

## Suggested Hosting Shape

```text
https://inventar.nica.network
  -> reverse proxy
  -> frontend container
  -> backend container
  -> PostgreSQL container/private service
```

## Useful Questions

- Can Docker Compose run long-term on this server?
- Which reverse proxy/server panel should we integrate with?
- Where should persistent app data live?
- What backup system already exists?
- Should the app be public behind login, or only reachable via VPN/internal network?
- Can Marc get SSH access for deployment/maintenance commands?

## Not Needed Yet

We are not asking for immediate deployment. First we want to confirm the expected server setup and access path.

