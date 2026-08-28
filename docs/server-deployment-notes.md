# Server Deployment Record

This file records the outcome of the original IT hosting discussion. It is no
longer a planning document.

## Outcome

The application went live at `https://inventory.nica.network` in August 2026.
Trebor provided:

- the `Marc@nica.network` SSH account;
- Docker and Docker Compose access;
- the `/opt/docker/inventory` application location;
- Apache reverse proxy routes to loopback-only frontend/backend ports;
- DNS and a valid HTTPS certificate for `inventory.nica.network`.

The app runs as three Docker services: PostgreSQL, FastAPI, and SvelteKit.
PostgreSQL is private to Docker; only Apache is public. Database data and image
uploads use persistent Docker volumes.

## Responsibility Split

Marc owns application development, GitHub history, manual releases, application
health checks, and coordination of data-level operations.

Trebor owns Apache, TLS, DNS, firewall, root-owned server configuration, and any
server-wide backup system.

## Remaining IT Confirmation

The following production requirement is not yet observable from Marc's account:

- automated database and upload backups;
- off-server destination and retention;
- monitoring of backup failures;
- periodic restore-test ownership.

## Current Documentation

- `docs/server-operations.md`: exact SSH/server layout and AI-agent rules.
- `docs/development-and-deployment-workflow.md`: local-to-production release
  process.
- `docs/production-runbook.md`: deployment, health, backup, restore, and
  rollback.

Keep this file as the historical IT handoff record. Update the operational
documents above when the live configuration changes.
