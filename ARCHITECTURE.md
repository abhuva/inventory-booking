# Architecture

## System Overview

```text
Desktop / phone browser
  -> SvelteKit frontend
  -> FastAPI backend
  -> PostgreSQL database
```

This is a single-tenant internal tool for a small circus-pedagogy team. It is not a SaaS product and does not need multi-tenant customer support complexity. It still needs strong correctness and baseline security because it runs over a network and stores operational state.

## Product Context

The inventory contains two fundamentally different inventory modes:

- `tracked`: exact unique assets, such as a specific aerial stand, trampoline, unicycle, or large apparatus.
- `stock`: quantity-based assets, such as juggling balls, cones, scarves, or similar items where individual pieces are not tracked.

The system must answer both:

- where is this exact aerial stand and who has it?
- how many red juggling balls are available in this location for a future booking?

## Backend Responsibilities

FastAPI owns business rules and API validation:

- authentication and authorization
- admin/user role enforcement
- asset, category, user, and location management
- tracked asset location, holder, status, and QR lifecycle
- stock quantity by location
- QR code generation, assignment, and resolution
- booking creation and time-range conflict prevention
- checkout, return, transfer, maintenance, damage, lost, and retired workflows
- item events and audit logging

The backend must enforce conflict prevention in transactions. Frontend checks are only UX assistance.

## Frontend Responsibilities

SvelteKit provides the low-friction user interface:

- dashboard
- asset search and detail
- stock overview by location
- location overview
- booking creation and availability feedback
- QR scan and QR assignment flows
- checkout and return screens
- maintenance/damage views
- simple admin settings

The UI should be usable on desktop and phones from the beginning because QR and checkout workflows are phone-first.

## Database Direction

PostgreSQL is the source of truth for operational data:

- users and roles
- locations
- categories
- assets with `tracked` and `stock` modes
- stock levels per location
- QR codes
- bookings and booking lines
- checkouts and returns
- item events
- audit logs

Operational state must not live in Markdown/YAML files.

## Initial Domain Boundaries

- `users`: small local team, initially `admin` and `user` roles only.
- `locations`: rooms, storage, vehicles, project sites, external spaces, person homes, repair, unknown.
- `inventory`: categories, assets, tracked asset state, stock levels.
- `qr`: opaque QR labels mapped to assets or workflow actions.
- `bookings`: future reservations for exact tracked assets or stock quantities.
- `movements`: checkout, return, transfer, and stock movements.
- `audit`: append-only event and security-relevant mutation history.

## Tracked Assets

Tracked assets represent exact physical objects.

Important fields:

```text
id
name
category_id
status
condition
home_location_id
current_location_id
current_holder_user_id
serial_number
asset_tag
replacement_value
notes
```

Tracked assets can have QR labels and event history.

## Stock Assets

Stock assets represent quantities of a thing.

Important fields:

```text
id
name
category_id
unit_name
notes
```

Quantities live in `stock_levels` per location:

```text
asset_id
location_id
quantity_total
quantity_reserved
quantity_checked_out
```

Available stock is computed from total quantity, reservations, checkouts, and unavailable states.

## Booking Direction

Bookings contain lines. A line can reserve either:

- one exact tracked asset
- a quantity of a stock asset

Availability differs by mode:

```text
tracked asset:
  unavailable if exact asset has overlapping active booking, active checkout, maintenance, damaged, lost, or retired state

stock asset:
  unavailable if requested quantity exceeds available stock for the requested time range and location scope
```

Time range conflict rule:

```sql
existing.starts_at < requested.ends_at
AND existing.ends_at > requested.starts_at
```

## Users And Roles

Only two roles are planned initially:

- `admin`: user management, categories, conflict overrides, destructive/retirement actions, audit review.
- `user`: inventory view, booking, checkout, return, transfer, QR scan, damage/missing reports.

Even for a small trusted team, all state-changing actions must record actor and timestamp.

## Security Baseline

Security is part of the architecture, not a later add-on:

- password hashing with a modern algorithm
- HTTP-only secure cookies for browser sessions
- CSRF protection for browser mutations
- strict CORS
- Pydantic request validation
- SQLAlchemy parameterization, no user-built SQL strings
- authorization checks in backend services
- rate limiting for login
- audit logs for mutations and admin actions
- dependency and static security checks in CI/local checks

See `docs/security/security-review.md` for the review workflow.

## AI-Agent-Friendly Modularity

Keep files small and domain-scoped. Backend modules follow this pattern:

```text
<domain>/models.py
<domain>/schemas.py
<domain>/router.py
<domain>/service.py
```

Rules:

- routers handle HTTP only
- schemas handle API validation and serialization
- services contain business logic
- models define persistence
- availability logic is isolated and heavily tested
- security utilities live centrally

## Tradeoffs

- Explicitly model both tracked and stock assets from the first schema to match real inventory behavior.
- Keep roles simple to avoid unnecessary permission-matrix complexity.
- Use Docker Compose for the full local stack, but keep backend and frontend runnable without Docker for fast iteration.
- Add audit/events without implementing full event sourcing.
- Start with online-first workflows; offline/PWA queueing can come later if QR workflows prove unreliable without it.

## Deployment Direction

Initial deployment should use Docker Compose or equivalent services:

- PostgreSQL
- FastAPI backend
- SvelteKit frontend
- reverse proxy with HTTPS
- backup job

Backups are mandatory before production use: daily dump, off-server copy, and periodic restore test.
