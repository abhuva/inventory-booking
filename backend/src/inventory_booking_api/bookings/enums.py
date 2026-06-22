from enum import StrEnum


class BookingStatus(StrEnum):
    RESERVED = "reserved"
    CANCELLED = "cancelled"
    CHECKED_OUT = "checked_out"
    COMPLETED = "completed"
