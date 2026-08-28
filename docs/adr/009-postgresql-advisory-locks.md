# ADR 009: Use PostgreSQL Advisory Locks For Inventory Mutations

**Status**: Accepted | **Date**: 2026-08-05 |
**Participants**: Marc Bielert, implementation contributors

## Context

ADR 008 accepted service-level conflict checks for the local MVP but required a
stronger concurrency boundary before network deployment. Booking, basket,
checkout, return, transfer, and stock commands can race even when each request
performs correct availability validation.

The application is a small single-tenant system, but several commands affect the
same logical asset across different tables. Some conflicts also concern a row
that does not exist yet, which makes ordinary row locking incomplete.

Alternatives considered were:

- PostgreSQL exclusion constraints, which fit tracked date ranges but do not
  uniformly cover stock quantities and cross-workflow mutations;
- serializable transactions, which provide a broad guarantee but require retry
  handling for every affected command;
- row locks, which do not naturally lock absent future bookings or every
  aggregate availability input;
- transaction-scoped advisory locks using stable domain keys.

## Decision

We decided to acquire deterministic PostgreSQL transaction-scoped advisory
locks before validating and mutating high-risk state. Locks are keyed by logical
asset, booking, or checkout identifiers and are acquired in sorted order.

Booking, basket, checkout, return, stock, and movement command paths use these
locks. SQLite-based unit tests treat the helper as a no-op; opt-in PostgreSQL
concurrency tests exercise the production behavior.

## Consequences

- (+) Validation and mutation for one logical item are serialized across
  workflows.
- (+) Transaction-scoped locks release automatically on commit or rollback.
- (+) The design covers conflicts where no lockable database row exists yet.
- (+) Deterministic ordering reduces deadlock risk when a command touches
  multiple assets.
- (-) Correctness depends on every relevant command using the same key scheme.
- (-) SQLite tests cannot prove lock behavior; PostgreSQL concurrency tests
  remain necessary.
- (-) This is PostgreSQL-specific and would need redesign if the production
  database changed.
