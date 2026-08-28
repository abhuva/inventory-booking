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

The primary UI is desktop-first because planning, admin, booking, and inventory correction work benefit from tabs, forms, and side-by-side detail panels. Mobile should not be a compressed version of the desktop workspace. A later dedicated field/mobile route should focus on QR lookup, moving items, checkout/return, and damage reporting with large task-based controls.

## Database Direction

PostgreSQL is the source of truth for operational data:

- users and roles
- persons and external/team contacts
- locations
- categories
- asset definitions with `tracked` and `stock` modes
- tracked units for exact physical items
- stock batches for quantity groups by location, holder, and state
- active baskets for temporary holds
- QR codes
- asset image metadata
- bookings and booking lines
- checkouts and returns
- item events
- audit logs

Operational state must not live in Markdown/YAML files.

Asset photo binaries are stored on the backend filesystem in a persistent Docker volume.
PostgreSQL stores only metadata and the server-generated storage path. The system stores
processed derivatives only, not original camera files.

## Initial Domain Boundaries

- `users`: small local team, initially `admin` and `user` roles only.
- `persons`: people or groups tied to bookings and responsibility; types are `admin`, `user`, `team`, and `external`.
- `locations`: rooms, storage, vehicles, project sites, external spaces, person homes, repair, unknown.
- `inventory`: categories, asset definitions, tracked units, stock batches, and derived stock-level compatibility views.
- `qr`: opaque QR labels mapped to assets or workflow actions.
- `bookings`: future reservations for exact tracked assets or stock quantities, with temporary basket holds.
- `movements`: checkout, return, transfer, and stock movements.
- `audit`: append-only event and security-relevant mutation history.

## Tracked Assets

Tracked assets represent exact physical objects. The shared description lives on the asset definition; current physical state lives on `tracked_units`.

Important fields:

```text
id
asset_id
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

Stock assets represent quantities of a thing. The shared description lives on the asset definition; physical quantities live in `stock_batches`.

Important fields:

```text
id
name
category_id
unit_name
notes
```

Quantities are exposed through compatible `stock_levels` API shapes, but internally live in stock batches:

```text
asset_id
location_id
quantity
status
holder_user_id
checkout_line_id
```

Available stock is computed from total quantity, reservations, checkouts, and unavailable states.

## Booking Direction

Bookings contain lines. A line can reserve either:

- one exact tracked asset
- a quantity of a stock asset

Bookings can also be created from an active basket. Basket lines temporarily hold tracked items or stock quantities for a user/person/date range until the basket is confirmed or cancelled.

Availability differs by mode:

```text
tracked asset:
  unavailable if exact asset has overlapping active booking, active checkout, maintenance, damaged, lost, or retired state

stock asset:
  unavailable if requested quantity exceeds available stock for the requested time range and location scope
```

The stock tab heatmap uses the same concepts for planning visibility. Stock rows show proportional availability by quantity. Tracked rows show binary availability: available or unavailable.

Time range conflict rule:

```sql
existing.starts_at < requested.ends_at
AND existing.ends_at > requested.starts_at
```

## Users And Roles

Two roles are currently implemented:

- `admin`: user management, categories, destructive/retirement actions, and audit review.
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

## Production Deployment

Production is live at `https://inventory.nica.network` with this topology:

```text
Apache reverse proxy and TLS
  -> SvelteKit frontend on 127.0.0.1:3000
  -> FastAPI backend on 127.0.0.1:8000
  -> PostgreSQL on the private Docker network
```

The application runs from a Git checkout of `main` under
`/opt/docker/inventory`. Releases are manual: the server pulls a reviewed commit,
rebuilds the Compose project, applies Alembic migrations, and checks service
health. Application secrets and the live Compose file remain server-local.

PostgreSQL data and uploaded photos use persistent Docker volumes. The required
backup baseline remains daily database and upload backups, an off-server copy,
and periodic restore tests. During the production audit on 2026-08-28 UTC,
documentation and manual commands existed, but server-wide automated backup
coverage still required confirmation from IT.

See `docs/server-operations.md` and `docs/production-runbook.md`.
