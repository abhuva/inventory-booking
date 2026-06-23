from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from inventory_booking_api.persons.enums import PersonType


class PersonCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=160)
    person_type: PersonType = PersonType.UNKNOWN
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=80)
    notes: str | None = None
    user_id: UUID | None = None
    is_active: bool = True


class PersonUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    person_type: PersonType | None = None
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=80)
    notes: str | None = None
    user_id: UUID | None = None
    is_active: bool | None = None


class PersonRead(BaseModel):
    id: UUID
    display_name: str
    person_type: PersonType
    email: EmailStr | None
    phone: str | None
    notes: str | None
    user_id: UUID | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
