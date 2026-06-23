from enum import StrEnum


class PersonType(StrEnum):
    TEAM = "team"
    EXTERNAL = "external"
    ORGANIZATION = "organization"
    UNKNOWN = "unknown"
