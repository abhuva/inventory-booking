from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from inventory_booking_api.core.models import Base, IdMixin, TimestampMixin
from inventory_booking_api.users.enums import UserRole


class User(IdMixin, TimestampMixin, Base):
    """Application user for the small internal team."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole, name="user_role", values_callable=lambda enum: [item.value for item in enum]
        ),
        nullable=False,
        default=UserRole.USER,
    )
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
