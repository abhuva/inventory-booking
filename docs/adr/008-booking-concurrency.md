# ADR 008: Booking Concurrency For Local MVP

## Status

Accepted

## Context

Booking conflicts are currently enforced in the service layer by checking overlapping active bookings before creation.
This is correct for normal request flow, but it is not a database-level guarantee against two concurrent requests racing each other.

The expected deployment is a small local team with low write concurrency.

## Decision

For the local MVP, keep service-level booking conflict checks and defer database-level concurrency hardening.

Before larger deployment or external network exposure, revisit one of these options:

- PostgreSQL exclusion constraints for tracked booking ranges.
- Serializable transaction isolation around booking creation.
- Advisory locks keyed by asset/location during booking creation.

## Consequences

- Checkout and return workflows can proceed without adding premature database complexity.
- The residual risk is documented and acceptable for current usage.
- Future hardening has clear implementation candidates.
