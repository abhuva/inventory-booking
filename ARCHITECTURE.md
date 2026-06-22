# Architecture

## System Overview

```text
Desktop / phone browser
  -> SvelteKit frontend
  -> FastAPI backend
  -> PostgreSQL database
```

The first version is a responsive web app. PWA support, native mobile, object storage, notifications, and background workers can be added after the operational core is reliable.

## Backend Responsibilities

FastAPI owns business rules and API validation:

- authentication and authorization
- item, category, user, role, and location management
- QR code generation, assignment, and resolution
- booking creation and time-range conflict prevention
- checkout, return, transfer, maintenance, damage, lost, and retired workflows
- item events and audit logging

The backend must enforce conflict prevention in transactions. Frontend checks are only UX assistance.

## Frontend Responsibilities

SvelteKit provides the low-friction user interface:

- dashboard
- item search and item detail
- location overview
- booking creation and availability feedback
- QR scan and QR assignment flows
- checkout and return screens
- maintenance/damage views
- admin settings

The UI should be usable on desktop and phones from the beginning.

## Database Direction

PostgreSQL is the source of truth for operational data:

- users and roles
- items and categories
- locations
- QR codes
- bookings and booking items
- checkouts and returns
- item events
- audit logs

Planned implementation path:

1. SQLAlchemy models and Alembic migrations.
2. Constraints for unique active QR assignment and valid state transitions where practical.
3. Transactional service layer for availability, checkout, return, and transfer operations.
4. Integration tests around conflict prevention.

## Initial Domain Boundaries

- `items`: physical inventory records and current item state.
- `locations`: rooms, vehicles, people, project sites, repair shops, and unknown/missing locations.
- `bookings`: planned reservations with time ranges.
- `checkouts` and `returns`: actual movement and condition records.
- `qr_codes`: opaque labels mapped to items through lifecycle states.
- `item_events`: append-only operational history.
- `audit_logs`: who changed what and when.

## Availability Rule

Two bookings conflict when:

```sql
existing.starts_at < requested.ends_at
AND existing.ends_at > requested.starts_at
```

An item is unavailable when it has an overlapping active booking, is checked out, is in maintenance, is damaged without approval, is lost, or is retired.

## Tradeoffs

- Use a split backend/frontend repo to keep FastAPI and SvelteKit lifecycles independent.
- Use Docker Compose for the full stack, but keep backend and frontend runnable without Docker for faster iteration.
- Start with direct physical-item bookings. Category quantity booking and kit auto-assignment are later features.
- Use opaque QR tokens instead of item IDs so labels can be retired, replaced, and audited safely.

## Deployment Direction

Initial deployment should use Docker Compose or equivalent services:

- PostgreSQL
- FastAPI backend
- SvelteKit frontend
- reverse proxy with HTTPS
- backup job

Backups are mandatory before production use: daily dump, off-server copy, and periodic restore test.
