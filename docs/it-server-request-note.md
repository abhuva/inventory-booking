## App Summary

- Internally used inventory management.
- Stack:
  - SvelteKit frontend
  - FastAPI backend
  - PostgreSQL database
  - Docker Compose runtime

## Stuff thats most likely needed
- Subdomain, likely `inventory.nica.network`.
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
https://inventory.nica.network
  -> reverse proxy
  -> frontend container
  -> backend container
  -> PostgreSQL container/private service
```


