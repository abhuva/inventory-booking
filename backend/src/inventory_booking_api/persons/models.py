from uuid import UUID

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from inventory_booking_api.core.models import Base, IdMixin, TimestampMixin
from inventory_booking_api.persons.enums import PersonType


class Person(IdMixin, TimestampMixin, Base):
    """Real-world person or organization used in operational inventory workflows."""

    __tablename__ = "persons"

    display_name: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    person_type: Mapped[PersonType] = mapped_column(
        Enum(
            PersonType,
            name="person_type",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
        default=PersonType.UNKNOWN,
    )
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), unique=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
