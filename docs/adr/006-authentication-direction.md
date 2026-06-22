# ADR-006: Authentication Direction

## Status

Accepted

## Context

The app is internal and used by a small local team, but mutation endpoints must not be open on the network. Full browser login/session work is its own implementation slice.

## Decision

Use HTTP-only session-cookie authentication as the target browser auth model. Until that slice is implemented, mutating API endpoints require a temporary internal API token through the `X-API-Token` header.

## Consequences

- Read endpoints can be exercised during early development.
- Write endpoints are not accidentally unauthenticated while login is pending.
- The temporary token dependency is isolated in `core/security.py` so it can be replaced by session/user dependencies later.
- The token is not sufficient for production deployment; production requires real user login, CSRF protection, session expiry, and role checks.
