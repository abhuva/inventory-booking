# ADR-005: Security Review For API And Database Changes

## Status

Accepted

## Context

The app is internal but network-accessible. It will be developed with AI agents, so regular security review must be explicit and repeatable.

## Decision

Every API/database feature must include a security review checklist and tests for expected authorization and invalid input behavior.

## Consequences

- Security review is part of normal implementation, not a final hardening phase.
- Red-team style tests should be added for bookings, auth, stock changes, and admin overrides.
- Dependency and static security checks should be automated as the project matures.
