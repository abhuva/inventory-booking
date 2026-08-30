from decimal import ROUND_HALF_UP, Decimal

DAILY_RATE_QUANTUM = Decimal("0.000001")


def calculate_daily_rental_rate(
    replacement_value: Decimal | None,
    recoup_days: int | None,
    maintenance_cost_per_day: Decimal | None,
    profit_margin_percent: Decimal | None,
) -> Decimal | None:
    """Calculate the configured price for one item and one started rental day."""

    if (
        replacement_value is None
        or recoup_days is None
        or maintenance_cost_per_day is None
        or profit_margin_percent is None
    ):
        return None
    base_daily_cost = replacement_value / Decimal(recoup_days)
    margin_multiplier = Decimal("1") + profit_margin_percent / Decimal("100")
    return ((base_daily_cost + maintenance_cost_per_day) * margin_multiplier).quantize(
        DAILY_RATE_QUANTUM,
        rounding=ROUND_HALF_UP,
    )
