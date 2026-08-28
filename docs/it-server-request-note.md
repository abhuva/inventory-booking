# IT Server Request Outcome

This note was the original short handoff to Trebor. Hosting is now active.

## Completed

- [x] `https://inventory.nica.network` subdomain.
- [x] Valid HTTPS certificate and HTTP-to-HTTPS redirect.
- [x] Docker and Docker Compose runtime.
- [x] Apache reverse proxy to frontend and backend loopback ports.
- [x] Persistent PostgreSQL and upload volumes.
- [x] PostgreSQL not exposed publicly.
- [x] SSH access for Marc with Docker group membership.

## Still To Confirm With IT

- [ ] Automated PostgreSQL and upload-volume backup schedule.
- [ ] Off-server backup destination and retention period.
- [ ] Backup-failure monitoring.
- [ ] Periodic restore-test owner and schedule.

See `docs/server-deployment-notes.md` for the responsibility split and
`docs/server-operations.md` for the active configuration.
