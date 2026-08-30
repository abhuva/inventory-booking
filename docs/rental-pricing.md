# Rental Pricing

## Source And Formula

The initial pricing model follows `Materialverleih + Kalkulation.ods` from the
NICA Vereinsverwaltung documents. The application deliberately uses the
existing per-item replacement value as the simplified base value instead of
modeling material and labor components.

```text
daily unit price =
  (base value / recoup rental days + maintenance cost per unit/day)
  * (1 + profit margin percent / 100)

booking line price =
  daily unit price * charged rental days * quantity
```

Money is calculated with decimal arithmetic in the backend. Daily unit prices
are stored with six fractional digits; booking line totals are rounded to euro
cents using round-half-up.

## Charged Days

Every started 24-hour period is charged, with a minimum of one day:

- up to and including 24 hours: 1 day
- more than 24 hours and up to 48 hours: 2 days
- and so on

## Persistence

Asset definitions store:

- `replacement_value`
- `rental_recoup_days`
- `rental_maintenance_cost_per_day`
- `rental_profit_margin_percent`

All four values are required for a calculated daily rate. Partial or absent
configuration leaves the asset unpriced.

Booking lines snapshot the calculated daily unit price at creation together
with charged days and the rounded line total. Later asset pricing changes do
not alter existing bookings. Changing an existing booking's dates recalculates
its charged days and total using the snapshotted daily rate.

Existing booking lines are intentionally not backfilled by the migration. A
booking total is unavailable when any of its lines is unpriced, so the UI never
presents a partial sum as the complete rental price.
