# Implementation Plan

## Principles

- Build backend correctness before UI convenience.
- Support both `tracked` and `stock` assets from the first database schema.
- Keep modules small and domain-oriented for AI-agent maintainability.
- Treat security review as part of every API/database task.
- Prefer narrow vertical slices with tests over broad untested scaffolding.

## Dependency Map

```text
Repository baseline
  -> architecture/security docs
  -> database foundation
  -> user/auth foundation
  -> locations/categories/assets
  -> stock levels and asset events
  -> bookings and availability
  -> checkout/return/movement workflows
  -> QR workflows
  -> frontend screens
  -> deployment hardening
```

## Phase 0: Repository And Architecture Baseline

Status: complete

- [x] Root docs and agent entry point
- [x] FastAPI skeleton
- [x] SvelteKit skeleton
- [x] Local environment examples
- [x] Docker Compose service topology
- [x] Docker local startup validation
- [x] Architecture update for tracked and stock assets
- [x] ADRs for core decisions
- [x] Security review workflow
- [x] Auth direction ADR

Dependencies: none.

## Phase 1: Backend Foundation

Goal: database-backed backend with migrations, modular domains, and a security-aware base.

### 1.1 Database Foundation

Dependencies: Phase 0.

- [x] SQLAlchemy async engine and session dependency
- [x] Alembic configuration
- [x] initial migration path
- [x] database health endpoint
- [x] Docker-compatible migration command
- [x] tests for settings/model metadata

### 1.2 User And Auth Foundation

Dependencies: 1.1.

- [x] `users` model with `admin` and `user` roles
- [x] password hash storage fields
- [x] active/disabled state
- [x] session/auth architecture decision
- [x] initial admin seed strategy
- [x] temporary internal token authorization helper for mutation endpoints
- [x] session-cookie login/logout/me endpoints
- [x] password hashing with Argon2
- [x] tests for authenticated mutation guard
- [x] admin-only user management endpoints
- [x] CSRF double-submit protection for session mutations
- [x] tests for admin/user role enforcement

### 1.3 Locations And Categories

Dependencies: 1.1, partial 1.2 for actor/audit later.

- [x] `locations` model with location types
- [x] `categories` model
- [x] create/list/get/update APIs
- [x] validation schemas
- [x] service tests
- [x] temporary write-token guard on mutation endpoints
- [x] session-cookie guard on mutation endpoints

### 1.4 Inventory Assets

Dependencies: 1.1, 1.3.

- [x] `assets` model with `tracked` and `stock` modes
- [x] tracked asset fields: status, condition, home/current location, holder
- [x] stock asset fields: unit name
- [x] `stock_levels` model per asset/location
- [ ] constraints preventing stock levels on tracked-only usage where practical
- [x] create/list/get/update APIs
- [x] event creation for asset mutations
- [x] tests for tracked vs stock validation

### 1.5 Audit And Events

Dependencies: 1.1, 1.2, 1.4.

- [x] `item_events` model
- [x] `audit_logs` model
- [ ] event writer service
- [ ] audit writer service
- [ ] tests that inventory mutations write events/audit records
- [x] initial event/audit writes for asset create/update
- [x] actor-aware audit/event writer helpers

## Phase 2: Booking And Availability Core

Goal: reliable reservation logic before checkout/return UI.

### 2.1 Booking Schema

Dependencies: Phase 1.

- [ ] `bookings` model
- [ ] `booking_lines` model supporting tracked assets and stock quantities
- [ ] booking statuses
- [ ] date range validation
- [ ] tests for invalid ranges and invalid lines

### 2.2 Availability Service

Dependencies: 2.1.

- [ ] tracked asset overlap logic
- [ ] stock quantity overlap logic
- [ ] unavailable status handling
- [ ] admin override path design
- [ ] transaction boundary for booking creation
- [ ] red-team tests for conflict bypass attempts

### 2.3 Booking API

Dependencies: 2.2.

- [ ] create booking
- [ ] list bookings
- [ ] get booking detail
- [ ] cancel booking
- [ ] availability preview endpoint
- [ ] security review for all mutation endpoints

## Phase 3: Operational Workflows

Goal: support real equipment movement and accountability.

### 3.1 Checkout

Dependencies: Phase 2.

- [ ] checkout records
- [ ] checkout tracked assets
- [ ] checkout stock quantities
- [ ] condition-out fields
- [ ] event/audit writes
- [ ] tests for duplicate checkout and insufficient stock

### 3.2 Return

Dependencies: 3.1.

- [ ] return records
- [ ] partial returns
- [ ] condition-in fields
- [ ] damaged/missing handling
- [ ] event/audit writes
- [ ] tests for over-return and damaged return flows

### 3.3 Transfers And Maintenance

Dependencies: 1.4, 1.5.

- [ ] transfer tracked asset location/holder
- [ ] transfer stock between locations
- [ ] maintenance start/complete
- [ ] mark damaged/lost/retired
- [ ] tests for invalid state transitions

## Phase 4: QR Workflows

Goal: phone-friendly lookup and assignment.

Dependencies: Phase 1 inventory, Phase 3 movement flows.

- [ ] `qr_codes` model
- [ ] generate opaque QR tokens
- [ ] assign QR to tracked asset
- [ ] resolve assigned QR
- [ ] handle unassigned/retired/lost QR labels
- [ ] QR scan frontend route
- [ ] red-team tests for QR enumeration and unauthorized assignment

## Phase 5: Frontend MVP

Goal: usable internal workflow over the backend.

Dependencies: backend APIs for the target workflow.

- [ ] app shell and navigation
- [ ] login screen
- [ ] dashboard
- [ ] asset list/search
- [ ] asset detail with event history
- [ ] stock by location view
- [ ] location list/detail
- [ ] booking creation form
- [ ] availability feedback
- [ ] checkout screen
- [ ] return screen
- [ ] QR scan/assignment screens
- [ ] admin user/category screens

## Phase 6: Reliability And Deployment

Dependencies: stable MVP.

- [ ] HTTPS reverse proxy setup
- [ ] backup job
- [ ] restore test documentation
- [ ] dependency audit automation
- [ ] security static analysis automation
- [ ] production environment checklist
- [ ] deployment runbook

## Current Next Slice

Continue Phase 1 with authorization refinement and audit services:

- apply actor-aware audit helpers to category/location/stock mutations
- add dedicated audit query endpoints for admins
- add frontend login and inventory management screens
