from enum import StrEnum


class CheckoutStatus(StrEnum):
    CHECKED_OUT = "checked_out"
    PARTIALLY_RETURNED = "partially_returned"
    RETURNED = "returned"
