# Implementation Plan

## Current Focus: Option C Inventory Refactor

Goal: split catalog descriptions from physical inventory state.

Target model:

```text
Asset / ItemDefinition
  shared item description: name, category, description, photo, unit, tracking mode

TrackedUnit
  one exact physical object, quantity always 1

StockBatch
  physical quantity group, can split/merge/move/checkout partially
```

## Principles

- Keep backend business rules authoritative.
- Preserve audit/item event history for mutations.
- Keep public routes stable where practical while the internals move to Option C.
- Do not duplicate photos/descriptions per physical split.
- Treat quantity movement, checkout, and return as high-risk logic with tests.

## Refactor Tasks

### 1. Persistence

- [x] Add `tracked_units` table.
- [x] Add `stock_batches` table.
- [x] Migrate existing tracked `assets` rows into `tracked_units`.
- [x] Migrate existing `stock_levels` rows into `stock_batches`.
- [x] Keep existing `assets` rows as item definitions.
- [x] Keep asset images attached to definitions.

### 2. Backend Inventory API

- [x] Make `/assets` operate as item definitions with derived physical summaries.
- [x] Make tracked create create both definition and first unit.
- [x] Make tracked update write physical fields to the tracked unit.
- [x] Make stock create create definition only.
- [x] Replace stock-level service logic with stock-batch logic behind compatible routes.
- [x] Add explicit split/merge helpers for stock movement.

### 3. Booking And Availability

- [x] Keep booking lines definition-centered for stock.
- [x] Treat tracked booking lines as the first tracked unit for the selected definition during this transition.
- [x] Calculate stock availability from available stock batches.
- [x] Prevent overbooking with batch quantities.

### 4. Checkout And Return

- [x] Tracked checkout updates `tracked_units`.
- [x] Stock checkout splits available batches into checked-out batches.
- [x] Stock return merges quantity back into available destination batches.
- [x] Partial returns update checkout line progress.

### 5. QR

- [x] QR assignment targets tracked units conceptually.
- [x] Maintain current API compatibility during transition.

### 6. Frontend

- [x] Keep current Inventory tab working with compatible API shapes.
- [x] Show tracked state from tracked unit summaries.
- [x] Show stock state from stock batch summaries.
- [x] Add dedicated `Unit` and `Stock` right-panel tabs.

### 7. Verification

- [x] Add migration tests/regression tests for description vs physical state.
- [x] Add split/move/checkout/return stock-batch tests.
- [x] Run `.\scripts\check.ps1`.
- [x] Apply migration locally.
- [x] Commit refactor.

### 8. Location-Oriented Inventory UX

- [x] Add Inventory tab location filter.
- [x] Show tracked items by current unit location.
- [x] Show stock items when a stock batch exists at the selected location.
- [x] Summarize stock rows by logical asset/location stock levels.

### 9. Workspace Booking And Availability UX

- [x] Add persons as booking/contact entities with `admin`, `user`, `team`, and `external` types.
- [x] Add explicit booking person assignment in the basket and booking pipeline.
- [x] Show created/requested-by/person metadata on bookings.
- [x] Add booking table filters and sortable headers.
- [x] Make booking status, person, start date, and end date editable through backend availability checks.
- [x] Add persistent filter/tab UI settings where needed.
- [x] Add always-visible Basket and Account tabs.
- [x] Add editable current-account name, email, and password.

### 10. Destructive Operations

- [x] Add confirmed delete actions for assets, locations, persons, and bookings.
- [x] Repair nullable references when deleting locations and persons.
- [x] Block asset deletion when booking/checkout/return history would be broken.
- [x] Add regression tests for destructive operations.

### 11. Availability Heatmap

- [x] Cache heatmap results by range, bucket, location, and inventory/booking state fingerprint.
- [x] Add progress feedback during heatmap recalculation.
- [x] Add daily/weekly bucket toggle and client-side date-range zoom.
- [x] Avoid recalculation when only visual color thresholds change.
- [x] Include tracked unique items as binary 100%/0% availability rows.
