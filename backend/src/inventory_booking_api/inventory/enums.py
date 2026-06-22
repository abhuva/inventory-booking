from enum import StrEnum


class AssetType(StrEnum):
    TRACKED = "tracked"
    STOCK = "stock"


class AssetStatus(StrEnum):
    AVAILABLE = "available"
    RESERVED = "reserved"
    CHECKED_OUT = "checked_out"
    IN_TRANSFER = "in_transfer"
    MAINTENANCE = "maintenance"
    DAMAGED = "damaged"
    LOST = "lost"
    RETIRED = "retired"


class AssetCondition(StrEnum):
    UNKNOWN = "unknown"
    GOOD = "good"
    WORN = "worn"
    DAMAGED = "damaged"
    NEEDS_REPAIR = "needs_repair"
