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


class UserCreate(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=8, max_length=512)
    role: UserRole = UserRole.USER
    is_active: bool = True


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    password: str | None = Field(default=None, min_length=8, max_length=512)
    role: UserRole | None = None
    is_active: bool | None = None
