from enum import StrEnum


class LocationType(StrEnum):
    ROOM = "room"
    STORAGE = "storage"
    VEHICLE = "vehicle"
    PROJECT_SITE = "project_site"
    EXTERNAL_SPACE = "external_space"
    PERSON_HOME = "person_home"
    REPAIR = "repair"
    UNKNOWN = "unknown"
