# Inventory And Booking Tool Proposal

## Goal

Build an internal multi-user inventory and equipment lending system for a small team managing hundreds of physical items across several people, rooms, vehicles, and project locations.

The primary goal is operational reliability:

- know what equipment exists
- know where each item is
- know who currently has it
- reserve items for future use
- check items out and back in
- prevent accidental double-booking
- track damaged, missing, retired, or maintenance items
- use QR codes for fast item lookup and workflows

This should be a database-backed web application, not a Markdown/YAML-based system. Markdown exports can be added later if useful, but they should not be the source of truth.

## Recommended Stack

```text
PostgreSQL = source-of-truth database
FastAPI    = backend API and business logic
SvelteKit  = web frontend / mobile-friendly PWA
```

The system should start as a responsive web app that works well on desktop and phones. A native mobile app or Tauri app can be considered later if browser-based QR scanning or offline behavior is not sufficient.

## Architecture

```text
Users on desktop or phone
  |
  v
SvelteKit web app / PWA
  |
  v
FastAPI backend
  |
  v
PostgreSQL database
```

Optional later components:

```text
Object storage       = photos, damage reports, documents
Background worker    = reminders, overdue checks, exports
Email/Slack service  = notifications
Label printer flow   = QR code label printing
```

## PostgreSQL

PostgreSQL is the source of truth for all operational data.

It stores:

- items
- categories
- users
- roles
- locations
- bookings
- checkout and return records
- QR code assignments
- item events
- maintenance history
- damage/missing/lost state
- audit logs

Why PostgreSQL is the right fit:

- reliable with multiple concurrent users
- supports transactions for checkouts, returns, and conflict prevention
- strong data integrity through constraints
- good query capabilities for availability and reporting
- mature backup and restore tooling
- easy to host in Docker, on a VPS, or with managed database providers

Operational state should live in PostgreSQL, not in editable files.

## FastAPI

FastAPI is the backend service.

It owns the business logic and protects the database from invalid operations.

Responsibilities:

- authentication and authorization
- item creation and updates
- booking creation
- availability checks
- conflict detection
- QR code resolution
- QR code assignment
- checkout workflow
- return workflow
- transfer workflow
- maintenance workflow
- damage/missing/lost workflow
- audit logging
- API validation

Example API endpoints:

```text
GET    /items
GET    /items/{item_id}
POST   /items
PATCH  /items/{item_id}

GET    /locations
POST   /locations
GET    /locations/{location_id}/items

POST   /bookings
GET    /bookings/{booking_id}
POST   /bookings/{booking_id}/checkout
POST   /bookings/{booking_id}/return

POST   /qr-codes
POST   /qr-codes/{code}/assign
GET    /q/{code}

POST   /items/{item_id}/transfer
POST   /items/{item_id}/maintenance/start
POST   /items/{item_id}/maintenance/complete
POST   /items/{item_id}/mark-damaged
POST   /items/{item_id}/mark-lost
```

FastAPI is where critical rules should live, for example:

- an item cannot be checked out twice at the same time
- an item cannot be booked if it is already reserved in the same time range
- a lost or retired item cannot be booked
- a QR code cannot be assigned to two active items
- only certain roles can override conflicts
- every state-changing action creates an audit log entry

## SvelteKit

SvelteKit is the frontend application.

It provides the user interface for low-tech and non-tech users.

Main screens:

- dashboard
- item search
- item detail page
- location overview
- booking calendar
- create booking
- checkout screen
- return screen
- QR scan page
- maintenance/damaged items page
- user/admin settings

Why SvelteKit fits:

- good for fast, responsive web apps
- less boilerplate than many React setups
- strong routing and form handling
- can build mobile-friendly screens
- can become a Progressive Web App
- works cleanly with a separate FastAPI backend

## Mobile Approach

Start with a mobile-friendly web app / PWA.

The phone workflow should be:

```text
Open web app on phone
Scan QR code using camera
App resolves QR code
User sees item or action screen
```

A PWA is preferred for the first version because:

- one codebase for desktop and mobile
- no app store process
- easier updates
- faster MVP
- good enough for QR scanning in most internal workflows

Later options:

- Tauri mobile app using the same Svelte UI
- native app with React Native, Flutter, Swift, or Kotlin
- dedicated offline-first scanner app

Do not start with native mobile unless offline behavior or camera performance becomes a real blocker.

## QR Code Design

QR codes are critical and should be first-class records in the database.

A QR code should contain a stable URL or opaque token, not just the item name.

Example QR content:

```text
https://inventory.example.org/q/8J4K-X9P2
```

Database table concept:

```text
qr_codes
  id
  code
  assigned_item_id
  status
  created_at
  assigned_at
  retired_at
```

Recommended statuses:

```text
unassigned
assigned
retired
lost
replaced
```

Scanning behavior:

```text
Scan assigned QR code
  -> open item detail or workflow action

Scan unassigned QR code
  -> show assignment screen

Scan retired/lost QR code
  -> show warning
```

Recommended operational workflow:

1. Generate a batch of unassigned QR codes.
2. Print QR labels.
3. Stick a label on an item.
4. Scan the label.
5. App shows "unassigned QR code".
6. User searches/selects the item.
7. App assigns the QR code to that item.
8. Future scans open the item immediately.

Advantages of opaque QR codes instead of direct item IDs:

- labels can be reassigned if needed
- internal item IDs are not exposed
- damaged labels can be retired
- multiple QR labels can point to the same item if needed
- QR code lifecycle can be audited

## Domain Model

### Items

Each physical item has a stable internal ID.

Example fields:

```text
id
name
category_id
manufacturer
model
serial_number
asset_tag
home_location_id
current_location_id
status
condition
replacement_value
purchase_date
warranty_until
notes
created_at
updated_at
```

Recommended item statuses:

```text
available
reserved
checked_out
in_transfer
maintenance
damaged
lost
retired
```

Do not rely only on a single status field for history. Store item events as well.

### Locations

Locations should be first-class entities.

A location can be:

- storage room
- office
- studio
- vehicle
- person
- project site
- client site
- repair shop
- unknown/missing

This makes it possible to represent "Julia has the camera" and "the camera is in Studio A" using the same model.

Example fields:

```text
id
name
type
address
responsible_user_id
notes
active
```

### Users And Roles

Recommended roles:

```text
admin
manager
staff
viewer
```

Typical permissions:

```text
admin   = system settings, users, all overrides
manager = bookings, conflict overrides, inventory management
staff   = checkout, return, scan, view inventory
viewer  = read-only access
```

If the team already uses Google Workspace or Microsoft 365, use single sign-on if possible.

### Bookings

A booking is a planned reservation of items for a time range.

Example fields:

```text
id
title
project_name
requested_by_user_id
starts_at
ends_at
status
notes
created_at
updated_at
```

Recommended booking statuses:

```text
draft
reserved
checked_out
partially_returned
returned
cancelled
overdue
```

### Booking Items

A booking can reserve specific physical items.

```text
booking_id
item_id
status
```

Later, the system can support booking item categories instead of exact items, for example "2x LED panels". That can be added after the core specific-item workflow works reliably.

### Checkouts And Returns

A booking is the plan. A checkout is what actually happened.

Checkout fields:

```text
id
booking_id
checked_out_by_user_id
checked_out_to_user_id
from_location_id
to_location_id
checked_out_at
notes
```

Checkout item fields:

```text
checkout_id
item_id
condition_out
notes
```

Return fields:

```text
id
checkout_id
received_by_user_id
returned_at
return_location_id
notes
```

Return item fields:

```text
return_id
item_id
condition_in
status
notes
```

This supports partial returns and damaged/missing items.

### Item Events

Every important state change should create an event.

Example fields:

```text
id
item_id
event_type
occurred_at
actor_user_id
from_location_id
to_location_id
booking_id
checkout_id
return_id
notes
```

Example event types:

```text
created
updated
qr_assigned
moved
reserved
checked_out
returned
maintenance_started
maintenance_completed
damaged
lost
found
retired
```

Events provide auditability and make it possible to answer:

- where was this item last week?
- who checked it out?
- when was it returned?
- when did it become damaged?
- who changed the status?

## Availability Logic

Availability should be computed from:

- booking time ranges
- checkout status
- item status
- maintenance state
- lost/retired state
- location constraints

Time range conflict rule:

```text
A starts before B ends
AND
A ends after B starts
```

In SQL-like terms:

```sql
booking_a.starts_at < booking_b.ends_at
AND booking_a.ends_at > booking_b.starts_at
```

An item is unavailable if:

- it is already booked in an overlapping time range
- it is checked out and not returned
- it is in maintenance
- it is marked damaged and not approved for use
- it is lost
- it is retired
- it belongs to a fixed kit that is already unavailable

Conflict prevention should happen in the backend and database transaction, not only in the frontend.

## Kits And Bundles

The system should support both fixed kits and kit templates eventually.

### Fixed Kits

A fixed kit contains exact physical items.

Example:

```text
Sony FX6 Kit 01
  cam-fx6-001
  lens-2470-001
  battery-bpu-001
  battery-bpu-002
  charger-bpu-001
```

Good for camera cases, audio bags, and lighting cases.

### Kit Templates

A kit template describes requirements, not exact items.

Example:

```text
FX6 Basic Kit
  1x Sony FX6 body
  1x 24-70 lens
  2x BP-U battery
  1x charger
```

This is useful later, but it adds assignment complexity. For the MVP, fixed kits and direct item booking are enough.

## Essential Workflows

### Add Item

```text
Create item
Assign category
Assign home location
Assign current location
Optionally assign serial number and replacement value
Assign or print QR code
```

### Assign QR Code

```text
Scan unassigned QR code
Search/select item
Confirm assignment
Create qr_assigned event
```

### Create Booking

```text
Choose date range
Add items
System checks availability
Resolve conflicts if needed
Confirm booking
```

### Checkout

```text
Open booking
Scan items or select from booking list
Confirm recipient
Confirm destination/location
Record condition out
Create checkout records
Create item events
```

### Return

```text
Open active checkout
Scan returned items
Record condition in
Flag missing or damaged items
Update item location
Close or partially close booking
Create return records
Create item events
```

### Transfer Without Booking

```text
Scan item
Choose new location/person
Confirm move
Create moved event
```

### Maintenance

```text
Mark item in maintenance
Make unavailable
Add notes/photos if needed
Complete maintenance
Return to available state
Create events
```

## MVP Scope

The first version should focus on the operational core.

Build first:

- user login
- roles/permissions
- item database
- locations
- QR code generation
- QR code assignment
- QR scanning page
- item search
- booking creation
- availability/conflict checks
- checkout workflow
- return workflow
- item event history
- basic audit log
- basic admin UI

Do not build first:

- public customer booking storefront
- payments
- rental pricing engine
- contracts
- complex approval chains
- native mobile app
- complex kit auto-assignment
- advanced analytics

## Deployment

Recommended initial deployment:

```text
Docker Compose
  postgres
  fastapi-backend
  sveltekit-frontend
  reverse-proxy
  backup-job
```

Use HTTPS, even for internal tools.

Possible reverse proxies:

```text
Caddy
Nginx
Traefik
```

Caddy is attractive for a small team because HTTPS setup is simple.

Backups are mandatory. At minimum:

- daily PostgreSQL dump
- off-server backup copy
- periodic restore test

## Suggested Development Phases

### Phase 1: Data Model And Backend Core

- PostgreSQL schema
- FastAPI project setup
- authentication
- item/location/user models
- booking models
- event/audit models
- tests for availability logic

### Phase 2: Basic Web App

- SvelteKit setup
- login
- item list/search
- item detail
- location pages
- booking creation
- availability feedback

### Phase 3: QR And Operational Workflows

- QR code generation
- label export/printing
- QR assignment workflow
- phone scanning page
- checkout workflow
- return workflow
- transfer workflow

### Phase 4: Reliability And Admin

- role permissions
- audit log UI
- damaged/missing/maintenance flows
- backup automation
- deployment hardening

### Phase 5: Enhancements

- PWA install support
- offline-tolerant scanning queue
- email/Slack notifications
- overdue reminders
- packing lists
- public/customer request form
- native/Tauri mobile app if justified

## Key Design Decisions

- PostgreSQL is the source of truth.
- The app should be web-first and mobile-friendly.
- QR codes are opaque tokens mapped in the database.
- Checkouts and returns are explicit records, not just status changes.
- Item events provide history and auditability.
- Availability is computed from bookings, item state, and checkout state.
- Business rules live in FastAPI, not only in the frontend.
- Start with a PWA before building a native or Tauri mobile app.

## Short Recommendation

Build a PostgreSQL-backed FastAPI and SvelteKit web application.

Use SvelteKit for the low-tech user interface, FastAPI for business rules and APIs, and PostgreSQL for reliable multi-user state. Start with a responsive PWA for phone-based QR scanning. Add native mobile or Tauri later only if the browser-based scanner is not good enough in practice.
