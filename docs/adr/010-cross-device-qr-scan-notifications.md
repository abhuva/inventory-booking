# ADR 010: Poll Persisted Events For Cross-Device QR Scan Notifications

**Status**: Accepted | **Date**: 2026-08-30 |
**Participants**: Marc Bielert, implementation contributors

## Context

An authenticated user may scan an inventory QR label on a phone while keeping
the main inventory workspace open on a desktop. The desktop should notify that
same user and offer a direct link to the scanned asset. A scan notification must
not expose the QR token or become visible to another user.

Alternatives considered were:

- WebSockets, which provide bidirectional low-latency delivery but add connection
  handling and reverse-proxy configuration beyond this notification use case;
- server-sent events, which are simpler than WebSockets but still require a
  long-lived connection and proxy timeout configuration;
- Web Push, which can notify background or closed browsers but requires service
  workers, notification permission, and push subscription management;
- short polling of a persisted, user-scoped event feed.

## Decision

We decided to record successful authenticated QR scans as short-lived PostgreSQL
events and poll for them from the open workspace every three seconds. The QR
resolver remains a read-only request; the phone sends a separate idempotent POST
after the assigned asset has loaded successfully.

Events belong to the authenticated user, contain asset identifiers rather than
QR tokens, and are returned through a cursor-bounded authenticated feed. A
client-generated event identifier deduplicates retries. Events older than 24
hours are excluded from the feed and removed opportunistically when new scan
events are written.

## Consequences

- (+) A scan survives a short network interruption and can be consumed by any
  open workspace session for the same account.
- (+) The implementation uses the existing PostgreSQL, cookie session, CSRF, and
  Apache deployment model without new infrastructure.
- (+) The phone can still display the asset if notification delivery fails.
- (+) User scoping and omission of QR tokens keep the notification feed narrow.
- (-) Delivery can lag by up to the polling interval and creates a small amount
  of regular API traffic per open workspace.
- (-) Polling stops when the workspace is closed or the browser suspends the tab;
  background notifications would require Web Push later.
- (-) Opportunistic cleanup means expired rows remain stored until a later scan
  event is written.
