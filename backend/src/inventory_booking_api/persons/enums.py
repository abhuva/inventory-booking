from enum import StrEnum


class PersonType(StrEnum):
    ADMIN = "admin"
    USER = "user"
    TEAM = "team"
    EXTERNAL = "external"
