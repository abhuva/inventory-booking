from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from inventory_booking_api.users.enums import UserRole


class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str
    role: UserRole
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=512)
