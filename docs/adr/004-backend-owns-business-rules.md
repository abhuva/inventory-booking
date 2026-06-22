# ADR-004: Backend Owns Business Rules

## Status

Accepted

## Context

Bookings, checkout state, stock quantities, and conflict prevention are operationally important. Frontend-only validation is easy to bypass.

## Decision

All business rules must be enforced in FastAPI services and database transactions. The frontend can provide helpful feedback but cannot be trusted for correctness.

## Consequences

- Availability logic must be tested at service/database level.
- API endpoints must reject invalid state transitions.
- Database constraints should backstop critical invariants where practical.
