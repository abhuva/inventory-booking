from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

MONEY_QUANTUM = Decimal("0.01")


def calculate_rental_days(starts_at: datetime, ends_at: datetime) -> int:
    """Count every started 24-hour period, with a minimum charge of one day."""

    duration = ends_at - starts_at
    if duration <= timedelta(0):
        raise ValueError("Rental end must be after its start.")
    whole_days, remainder = divmod(duration, timedelta(days=1))
    return max(1, whole_days + (1 if remainder else 0))


def calculate_rental_total(
    daily_rate: Decimal | None,
    rental_days: int,
    quantity: int | None,
) -> Decimal | None:
    if daily_rate is None:
        return None
    charged_quantity = quantity if quantity is not None else 1
    return (daily_rate * rental_days * charged_quantity).quantize(
        MONEY_QUANTUM,
        rounding=ROUND_HALF_UP,
    )
