from enum import StrEnum


class BasketStatus(StrEnum):
    """Lifecycle states for temporary reservation baskets."""

    ACTIVE = "active"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
