# Architecture And Security Remediation Plan

## Purpose

This document records the architecture and security remediation that moved the
prototype to the current production deployment. Completed checklist items are
historical implementation evidence; ongoing operations are documented in the
production runbooks.

Operational truth remains in PostgreSQL. This document is planning and implementation state only.

## Current State

- Baseline commit before this plan: `e1e1535 Add line-level basket booking dates`.
- The app is a deployed FastAPI + SvelteKit + PostgreSQL internal service at
  `https://inventory.nica.network`.
- The recent line-level basket/booking date migration is implemented and tested.
- Deployment-blocking findings in this plan are implemented.
- Automated backup coverage remains an operational confirmation item with IT.

## Review Findings

### Security Findings

- [x] Read endpoints expose operational data without authentication.
  - Severity: critical before network deployment.
  - Affected areas: categories, locations, assets, stock levels, bookings, checkouts, returns.
  - Risk: unauthenticated users on the network can enumerate inventory, locations, booking history, checkout history, and return history.

- [x] Login has no rate limiting or failed-attempt throttling.
  - Severity: high.
  - Risk: online password guessing is limited only by infrastructure.

- [x] Production settings are not enforced at startup.
  - Severity: high.
  - Risk: the app can start in production with insecure cookies, default tokens, local DB credentials, or development CORS origins.

- [x] Security headers are missing.
  - Severity: medium.
  - Risk: weaker browser-side defense against clickjacking, content sniffing, referrer leakage, and script injection impact.

- [x] CSRF protection does not validate Origin/Referer.
  - Severity: medium.
  - Risk: double-submit CSRF is useful, but Origin validation is a stronger browser-session control.

- [x] Authorization is too broad for destructive/admin-like actions.
  - Severity: high.
  - Risk: any authenticated user can perform some destructive catalog/inventory mutations that should likely be admin or manager actions.

- [x] Booking and stock correctness rely on application-level validation without database locking.
  - Severity: high for concurrent use.
  - Risk: two concurrent requests can pass availability validation and overbook or mutate stock inconsistently.

- [x] Session lifecycle controls are incomplete.
  - Severity: medium.
  - Risk: sessions are not rotated/revoked on password or role changes, and expired sessions are not cleaned up automatically.

- [x] Upload handling lacks server-side re-encoding and malware scanning.
  - Severity: medium.
  - Risk: uploaded image content is validated but not normalized before being served back.

- [x] Frontend has hardcoded development login credentials.
  - Severity: medium.
  - Risk: unsafe expectation if the UI is deployed beyond local development.

### Architecture Findings

- [x] `bookings/service.py` is too large and mixes unrelated responsibilities.
  - Current state: booking commands, queries, heatmap, and availability now live in dedicated modules; `bookings/service.py` is a compatibility shim.

- [x] `inventory/asset_service.py` is too large and mixes catalog definitions, physical inventory state, stock batches, tracked units, transfers, deletion cleanup, and state transitions.
  - Current state: inventory logic is split across command, query, movement, stock, tracked-unit, and state helper modules; `inventory/asset_service.py` is a compatibility shim.

- [x] Availability is not a dedicated domain boundary.
  - Current state: baskets, booking validation, date-picker availability, and heatmap bucket/time logic share `bookings/availability.py`; heatmap keeps an optimized aggregate read path.

- [x] Transaction boundaries are implicit and inconsistent.
  - Current state: high-risk booking, basket, checkout, return, stock, and transfer operations use explicit command paths and Postgres advisory transaction locks.

- [x] Frontend `+page.svelte` is a god component.
  - Current state: route state/actions are split into auth, basket, booking, and inventory workspace state modules.

- [x] Frontend `InventoryPanel.svelte` and `app.css` are too large.
  - Current state: inventory table, asset detail tabs, stock editor, tracked-unit editor, QR, and image widgets are split into components; app styles are split into base, layout, components, and domain workspace files.

- [x] TypeScript API types are manually mirrored from backend schemas.
  - Current state: frontend public DTO aliases are derived from checked-in OpenAPI generated types; regeneration is documented in `README.md`.

## Dependency Map

- Security endpoint lockdown depends on frontend authenticated loading continuing to work.
- Login rate limiting depends only on auth router code and tests.
- Production settings enforcement depends on distinguishing local/docker/test from production via `APP_ENV`.
- Security headers can be implemented independently.
- Role permission hardening depends on a role/action matrix decision.
- Concurrency hardening depends on identifying command-level transaction boundaries and affected stock/booking rows.
- Availability extraction should happen before large booking-service refactors.
- Frontend state extraction should happen before splitting panels deeply.
- Production deployment config depends on finalized app/runtime settings.

## Implementation Plan

### Phase 0: Deployment-Blocking Security

- [x] Require authentication for all domain read endpoints.
  - [x] Categories list/detail.
  - [x] Locations list/detail.
  - [x] Assets list/detail.
  - [x] Stock levels list/detail.
  - [x] Bookings list/detail.
  - [x] Checkouts list/detail.
  - [x] Returns list/detail.
  - [x] Add tests proving unauthenticated reads return 401.
  - Depends on: frontend authenticated load flow.

- [x] Add login rate limiting.
  - [x] Limit repeated failed attempts per client IP and normalized email.
  - [x] Return 429 after threshold.
  - [x] Reset/allow after a short window.
  - [x] Add tests for lockout behavior.
  - Depends on: auth router.

- [x] Enforce production settings.
  - [x] Reject production startup with `SESSION_COOKIE_SECURE=false`.
  - [x] Reject production startup with `INTERNAL_API_TOKEN=local-dev-token`.
  - [x] Reject production startup with local default database credentials.
  - [x] Reject production startup with localhost CORS origins.
  - [x] Add settings tests.
  - Depends on: `APP_ENV` convention.

- [x] Add security headers middleware.
  - [x] `X-Content-Type-Options: nosniff`.
  - [x] `Referrer-Policy: same-origin`.
  - [x] `X-Frame-Options: DENY`.
  - [x] `Permissions-Policy` with restrictive defaults.
  - [x] CSP baseline for the API responses.
  - Depends on: none.

- [x] Remove hardcoded frontend login credentials.
  - [x] Empty login fields by default.
  - Depends on: none.

### Phase 1: Authorization And Session Hardening

- [x] Define role/action matrix.
  - [x] Admin-only: user management, categories, destructive deletes, forced state corrections.
  - [x] User: create bookings, basket usage, checkout/return, QR lookup, normal transfers.
  - [x] Decide whether a future `manager` role is needed.
  - Depends on: product decision.

- [x] Apply backend permission checks.
  - [x] Restrict category mutations.
  - [x] Restrict destructive asset/location/person/booking deletes.
  - [x] Restrict asset retirement/lost state transitions if needed.
  - [x] Add tests for admin/user behavior.
  - Depends on: role/action matrix.

- [x] Improve session lifecycle.
  - [x] Revoke sessions when a user is deactivated.
  - [x] Revoke other sessions on password change.
  - [x] Add expired-session cleanup helper or command.
  - Depends on: users/session service split.

- [x] Add Origin/Referer CSRF validation.
  - [x] Allow configured CORS origins.
  - [x] Reject unsafe browser requests from unexpected origins.
  - Depends on: production CORS settings.

### Phase 2: Concurrency And Data Integrity

- [x] Make transaction boundaries explicit.
  - [x] Commands commit once at the edge.
  - [x] Helper functions do not commit.
  - [x] Remove ad-hoc `commit=False` patterns.
  - Depends on: service extraction plan.

- [x] Add Postgres locking for high-risk operations.
  - [x] Booking create/update/cancel/delete.
  - [x] Basket line add/update/confirm/cancel.
  - [x] Checkout creation.
  - [x] Return creation.
  - [x] Stock transfer and tracked transfer.
  - Depends on: explicit commands.

- [x] Add concurrency tests.
  - [x] Double booking same tracked asset.
  - [x] Double booking same stock quantity.
  - [x] Checkout while stock is mutated.
  - [x] Return while stock is transferred.
  - Depends on: Postgres integration test path. Implemented as opt-in tests gated by `POSTGRES_TEST_DATABASE_URL` because they drop and recreate tables in the target database.

### Phase 3: Backend Modularity

- [x] Extract availability domain.
  - [x] Move overlap predicates and range validation into `availability`.
  - [x] Move stock/tracked availability calculations into `availability`.
  - [x] Make baskets, bookings, heatmap, and date picker use the same functions. Baskets, booking validation, preview, and date-picker availability now share `bookings/availability.py`; heatmap keeps optimized read-model aggregation while sharing bucket/time helpers.
  - Depends on: Phase 0 tests passing.

- [x] Split booking service.
  - [x] `bookings/commands.py`.
  - [x] `bookings/queries.py`.
  - [x] `bookings/heatmap.py`.
  - [x] `bookings/read_models.py` if needed. Not added: current read models are sufficiently isolated in `bookings/queries.py` and `bookings/heatmap.py`.
  - Depends on: availability extraction.

- [x] Split inventory service.
  - [x] `inventory/asset_commands.py`.
  - [x] `inventory/stock_commands.py`.
  - [x] `inventory/tracked_unit_commands.py`.
  - [x] `inventory/movement_commands.py`.
  - [x] `inventory/queries.py`.
  - [x] Extract shared tracked-unit projection and stock-batch helpers to `inventory/state.py`.
  - Depends on: transaction boundary plan.

- [x] Standardize audit writes.
  - [x] Add small audit helper for command modules.
  - [x] Keep append-only event history explicit.
  - [x] Apply paired audit/item-event helper across remaining command modules where it improves clarity.
  - Depends on: command modules.

### Phase 4: Frontend Modularity

- [x] Split API client by domain.
  - [x] `authApi`.
  - [x] `inventoryApi`.
  - [x] `locationsApi`.
  - [x] `bookingsApi`.
  - [x] `basketApi`.
  - [x] `adminApi`.
  - [x] `personsApi`.
  - [x] `operationsApi`.
  - Depends on: current API stability.

- [x] Move workspace state out of `+page.svelte`.
  - [x] Auth state/actions.
  - [x] Inventory state/actions.
  - [x] Booking state/actions.
  - [x] Basket state/actions.
  - Depends on: split API client.

- [x] Split large panels.
  - [x] Inventory table.
  - [x] Asset detail.
  - [x] Stock editor.
  - [x] Tracked unit editor.
  - [x] QR/image widgets.
  - Depends on: workspace state extraction.

- [x] Split CSS.
  - [x] Base styles.
  - [x] Layout styles.
  - [x] Component styles.
  - [x] Workspace global styles moved out of `app.css`.
  - Depends on: component split.

### Phase 5: Production Deployment

- [x] Add production deployment config.
  - [x] Production backend command without reload.
  - [x] Production frontend build/runtime.
  - [x] No exposed database port by default.
  - [x] Reverse proxy/TLS assumptions documented.
  - Depends on: production settings enforcement.

- [x] Add backup/restore runbook and manual commands.
  - [x] Document daily dump requirement.
  - [x] Document off-server copy requirement.
  - [x] Document restore test procedure.
  - Depends on: deployment target.

- [ ] Confirm production backup operation with IT.
  - [ ] Automated daily database and upload backup.
  - [ ] Off-server retention.
  - [ ] Failure monitoring and periodic restore-test ownership.

- [x] Add dependency/static security checks.
  - [x] Python dependency audit.
  - [x] npm audit or equivalent.
  - [x] Bandit baseline.
  - Depends on: CI/local check decision.

## Progress Log

- [x] Created this remediation plan.
- [x] Implemented Phase 0 security hardening: authenticated reads, login throttling, production settings guard, security headers, and empty login fields.
- [x] Implemented initial Phase 1 authorization/session hardening: admin-only category mutations, admin-only destructive deletes, CSRF Origin validation, and session revocation on sensitive account changes.
- [x] Restricted lost/retired asset state changes to admins and added a session cleanup helper.
- [x] Started availability extraction by moving pure date overlap, max-concurrency, and heatmap bucket helpers into `bookings/availability.py`.
- [x] Added production frontend Node runtime, production compose example, dev compose override, and production backup/restore runbook.
- [x] Ran dependency audits: npm audit found 0 vulnerabilities; pip-audit found no known vulnerabilities.
- [x] Ran Bandit backend static security scan; no issues identified after fixes.
- [x] Added Postgres transaction advisory locks around booking, basket, checkout, return, stock edit, and transfer mutations.
- [x] Added server-side image decode/re-encode for asset and location uploads; deferred antivirus scanning for internal-only deployment.
- [x] Extracted heatmap read-model/query/cache code from `bookings/service.py` into `bookings/heatmap.py`; `ruff` and backend tests pass.
- [x] Extracted booking read/query helpers into `bookings/queries.py`; `ruff` and backend tests pass.
- [x] Centralized basket preview, booking validation, and date-picker availability calculations in `bookings/availability.py`; `ruff` and backend tests pass.
- [x] Moved booking mutation commands into `bookings/commands.py` and reduced `bookings/service.py` to a compatibility shim; `ruff` and backend tests pass.
- [x] Extracted inventory tracked-unit projection and stock-batch read helpers into `inventory/state.py`; `ruff` and backend tests pass.
- [x] Extracted inventory asset/stock read queries and asset reference counts into `inventory/queries.py`; `ruff` and backend tests pass.
- [x] Split inventory mutation commands into asset, stock, movement, and tracked-unit command modules; `asset_service.py` is a compatibility shim and backend tests pass.
- [x] Replaced the booking `commit=False` flag with explicit `create_booking_without_commit` for basket confirmation composition; `ruff` and backend tests pass.
- [x] Added `write_audited_item_event` for explicit paired item-event/audit-log writes and applied it to asset definition create/update commands; `ruff` and backend tests pass.
- [x] Split frontend API calls into domain clients under `src/lib/api/` and migrated `+page.svelte` to use them; frontend check and lint pass.
- [x] Added opt-in PostgreSQL concurrency tests for double booking, stock overbooking, checkout-vs-stock mutation, and return-vs-transfer serialization. Run with `POSTGRES_TEST_DATABASE_URL=postgresql+asyncpg://... uv run --directory .\backend pytest .\tests\test_postgres_concurrency.py`; default backend suite skips them safely.
- [x] Applied `write_audited_item_event` to stock, movement, and tracked-unit command modules where item events and audit logs are paired; `ruff` and backend tests pass.
- [x] Split frontend global CSS into `app.css` imports plus `lib/styles/base.css` and `lib/styles/workspace.css`; frontend check and lint pass.
- [x] Extracted auth/account workspace state into `lib/workspace/auth-state.svelte.ts`; frontend check and lint pass.
- [x] Extracted basket workspace state into `lib/workspace/basket-state.svelte.ts`; frontend check and lint pass.
- [x] Extracted booking form, booking bundle, and availability state into `lib/workspace/booking-state.svelte.ts`; frontend check and lint pass.
- [x] Extracted inventory selection, form, stock, transfer, and state-change state into `lib/workspace/inventory-state.svelte.ts`; frontend check and lint pass.
- [x] Deployed the application at `https://inventory.nica.network` behind Apache
  TLS using a Git-backed, manually triggered Docker Compose release flow.
- [x] Reconciled server access, deployment, recovery, and AI-agent documentation
  with the live configuration on 2026-08-29.
