# ADR-001: Internal Single-Tenant Application

## Status

Accepted

## Context

The system is for a small local circus-pedagogy team. It is owned, built, and maintained internally. It is not a commercial SaaS product.

## Decision

Build a single-tenant internal web application with FastAPI, SvelteKit, PostgreSQL, and Docker Compose.

## Consequences

- No tenant model is needed.
- Simpler admin/user roles are enough initially.
- Security still matters because the app is reachable over a network.
- Operational correctness is more important than SaaS extensibility.
