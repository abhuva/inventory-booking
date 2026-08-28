# ADR 008: Booking Concurrency For Local MVP

**Status**: Superseded by ADR 009 | **Date**: 2026-06-23 |
**Participants**: Marc Bielert, implementation contributors

## Context

Booking conflicts were enforced in the service layer by checking overlapping
active bookings before creation. This was correct for normal request flow, but
it was not a database-level guarantee against two concurrent requests racing
each other.

The expected deployment is a small local team with low write concurrency.

## Decision

For the local MVP, we decided to keep service-level booking conflict checks and
defer database-level concurrency hardening.

Before larger deployment or external network exposure, revisit one of these options:

- PostgreSQL exclusion constraints for tracked booking ranges.
- Serializable transaction isolation around booking creation.
- Advisory locks keyed by asset/location during booking creation.

## Consequences

- Checkout and return workflows can proceed without adding premature database complexity.
- The residual risk is documented and acceptable for current usage.
- Future hardening had clear implementation candidates.

ADR 009 records the advisory-lock design implemented before production
deployment.
