# ADR-003: Admin And User Roles

## Status

Accepted

## Context

The app is used by a small trusted team. Complex role matrices would slow development and make authorization harder to audit.

## Decision

Start with two roles:

- `admin`
- `user`

## Consequences

- Authorization checks stay simple.
- Admin override flows must be explicit and audited.
- Additional roles can be added later if real workflows require them.
