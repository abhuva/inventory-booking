from enum import StrEnum


class ItemEventType(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    QR_ASSIGNED = "qr_assigned"
    MOVED = "moved"
    RESERVED = "reserved"
    CHECKED_OUT = "checked_out"
    RETURNED = "returned"
    MAINTENANCE_STARTED = "maintenance_started"
    MAINTENANCE_COMPLETED = "maintenance_completed"
    DAMAGED = "damaged"
    LOST = "lost"
    FOUND = "found"
    RETIRED = "retired"


class AuditAction(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    OVERRIDE = "override"
