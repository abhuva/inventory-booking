# ADR-006: Authentication Direction

## Status

Accepted

## Context

The app is internal and used by a small local team, but mutation endpoints must not be open on the network. Browser users need a simple login flow with revocable sessions.

## Decision

Use HTTP-only session-cookie authentication as the browser auth model. Store only hashed random session tokens in PostgreSQL. Seed the initial admin account through an explicit local command using `ADMIN_EMAIL` and `ADMIN_PASSWORD` environment variables.

## Consequences

- Mutating inventory endpoints require an authenticated session cookie.
- Sessions can be revoked server-side via logout or future admin tooling.
- Passwords are hashed with Argon2 through `pwdlib`.
- `SESSION_COOKIE_SECURE=false` is acceptable for local HTTP development only; production HTTPS must use secure cookies.
- CSRF protection is still required before production use for browser-triggered mutations.
- The legacy internal token helper remains only as a bootstrap/internal utility and should not protect normal user workflows.
