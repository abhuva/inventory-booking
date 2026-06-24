# Security Review Workflow

## Baseline Threats

Review every API/database change against these risks:

- unauthenticated access to protected endpoints
- unauthorized mutation by a normal user
- admin-only action reachable by user role
- booking conflict bypass
- stock quantity underflow or overbooking
- SQL injection through filters/search/sort parameters
- mass assignment of protected fields
- insecure direct object reference between users/resources
- CSRF on browser-triggered mutations
- stored XSS in notes, names, descriptions, or event text
- secrets or tokens in logs
- destructive actions without audit events

## Required Review For New Endpoints

- [ ] Endpoint requires authentication unless explicitly public.
- [ ] Authorization rule is documented in router or service tests.
- [ ] Browser mutation endpoints enforce CSRF protection.
- [ ] Request schema rejects unexpected fields where needed.
- [ ] Service validates state transitions server-side.
- [ ] Mutation writes audit/event records.
- [ ] Tests include at least one invalid/malicious request.
- [ ] No raw SQL is built from user-controlled strings.
- [ ] Errors do not leak secrets or stack traces.

## Automated Checks Target

Backend:

```powershell
uv run --directory .\backend ruff check .
uv run --directory .\backend pytest
```

Frontend:

```powershell
npm.cmd --prefix .\frontend run check
npm.cmd --prefix .\frontend run lint
npm.cmd --prefix .\frontend audit --audit-level=moderate
```

Planned additions:

- Python dependency audit
- Semgrep or Bandit for security-oriented static checks
- API abuse tests for auth, permissions, booking conflicts, stock underflow, and admin overrides

## Booking Endpoint Review (2026-06-22)

Reviewed endpoints:

- `POST /bookings`
- `POST /bookings/availability`
- `POST /bookings/{booking_id}/cancel`

Controls in place:

- Session authentication required for all booking mutations and availability previews.
- CSRF middleware covers browser-triggered booking mutations.
- Booking create schemas reject unexpected fields, including protected status/requester injection.
- Server-side validation rejects invalid ranges, duplicate lines, tracked conflicts, stock overbooking, stock-without-location, and unavailable assets.
- Booking create/cancel writes audit records; booking create writes item events.
- Admin conflict overrides are intentionally not implemented; ADR 007 requires explicit audited override design before adding them.

Residual risk:

- Concurrent booking creation is still enforced at service level, not by a database exclusion constraint or serializable transaction. This is acceptable for the local MVP but should be revisited before any larger multi-user deployment or external network exposure.

## Workspace Mutation Review (2026-06-24)

Reviewed endpoints:

- `PATCH /auth/me`
- `PATCH /bookings/{booking_id}`
- `DELETE /bookings/{booking_id}`
- `GET /bookings/availability/heatmap`
- `GET /bookings/availability/days`
- `GET /basket/active`
- `POST /basket`
- `PATCH /basket/{basket_id}`
- `POST /basket/{basket_id}/lines`
- `DELETE /basket/{basket_id}/lines/{line_id}`
- `POST /basket/{basket_id}/confirm`
- `POST /basket/{basket_id}/cancel`
- `DELETE /assets/{asset_id}`
- `DELETE /locations/{location_id}`
- `DELETE /persons/{person_id}`

Controls in place:

- Session authentication is required for current-account updates, baskets, booking edits, heatmap reads, and delete operations.
- CSRF middleware covers browser-triggered mutations.
- `PATCH /auth/me` only accepts email, display name, and password; role and active-state changes remain admin-only through `/users`.
- Booking date edits reuse backend availability validation instead of trusting the UI.
- Basket confirmation reuses booking creation validation and writes the resulting booking server-side.
- Location and person deletion repair nullable references before deleting.
- Asset deletion refuses to break booking, checkout, or return history.
- Delete operations and self-account updates write audit records.
- Regression tests cover current-account update, booking edit/delete, basket holds, heatmap availability, and destructive delete behavior.

Residual risk:

- Delete operations are intentionally broad admin/user mutations for the current trusted internal workflow. If stricter permissions are needed, add per-action authorization rules before external deployment.
- Asset deletion removes item events only when there are no booking/checkout/return references. This preserves operational history for used assets, but audit retention policy should be revisited before production.
