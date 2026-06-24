"""Add person reference to baskets and bookings.

Revision ID: 0013_booking_person
Revises: 0012_persons
Create Date: 2026-06-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_booking_person"
down_revision: str | None = "0012_persons"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("baskets", sa.Column("person_id", sa.Uuid(), nullable=True))
    op.add_column("bookings", sa.Column("person_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_baskets_person_id_persons"),
        "baskets",
        "persons",
        ["person_id"],
        ["id"],
    )
    op.create_foreign_key(
        op.f("fk_bookings_person_id_persons"),
        "bookings",
        "persons",
        ["person_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_bookings_person_id_persons"), "bookings", type_="foreignkey")
    op.drop_constraint(op.f("fk_baskets_person_id_persons"), "baskets", type_="foreignkey")
    op.drop_column("bookings", "person_id")
    op.drop_column("baskets", "person_id")
