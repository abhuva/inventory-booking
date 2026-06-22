# ADR-002: Tracked And Stock Assets

## Status

Accepted

## Context

The inventory contains exact unique items and quantity-based materials. Examples include exact aerial stands and trampolines, but also groups of balls, cones, and toys where individual pieces are not tracked.

## Decision

Model inventory assets with two modes:

- `tracked`: exact physical asset with current location, holder, status, QR labels, and event history.
- `stock`: quantity-based asset with stock levels per location.

## Consequences

- Availability logic must handle exact-asset conflicts and stock-quantity conflicts.
- Booking lines must support quantity.
- This avoids a painful schema refactor after real usage begins.
