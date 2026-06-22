# Implementation Plan

## Phase 0: Repository Baseline

- [x] Root docs and agent entry point
- [x] FastAPI skeleton
- [x] SvelteKit skeleton
- [x] Local environment examples
- [x] Docker Compose service topology

## Phase 1: Backend Core

- [ ] Database connection settings
- [ ] Alembic setup
- [ ] SQLAlchemy models for users, locations, items, QR codes, bookings, checkouts, returns, item events, audit logs
- [ ] Availability conflict service
- [ ] Tests for time-range overlap and unavailable item states

## Phase 2: Basic Web App

- [ ] App shell and navigation
- [ ] Item list/search
- [ ] Item detail
- [ ] Location overview
- [ ] Booking creation form
- [ ] Availability feedback

## Phase 3: QR And Operational Workflows

- [ ] QR code generation
- [ ] QR assignment flow
- [ ] QR scan page
- [ ] Checkout workflow
- [ ] Return workflow
- [ ] Transfer workflow

## Phase 4: Reliability And Admin

- [ ] Role permissions
- [ ] Audit log UI
- [ ] Maintenance, damaged, missing, lost, and retired flows
- [ ] Backup automation
- [ ] Deployment hardening
