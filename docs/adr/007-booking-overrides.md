# ADR 007: Booking Overrides

## Status

Accepted

## Context

The app is for a small trusted local team, but bookings still protect real equipment availability.
Silent conflict bypass would make the source of truth unreliable and would be hard to debug later.

## Decision

Booking creation must reject conflicts by default.

No request field may silently override conflicts. Any future override must be:

- admin-only
- explicit in the API payload
- explicit in the UI
- recorded in `audit_logs` with `AuditAction.OVERRIDE`
- visible in booking detail/history
- covered by red-team tests for normal-user bypass attempts

The current MVP has no override implementation. Admins must resolve conflicts manually by changing or cancelling the conflicting booking.

## Consequences

- The first operational version is stricter and simpler.
- Checkout and return workflows can rely on bookings as conflict-checked intent.
- If real usage needs exceptions, the override path will be added deliberately instead of as a hidden escape hatch.
