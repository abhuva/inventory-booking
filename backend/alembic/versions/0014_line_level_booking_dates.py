"""Add line-level booking and basket dates.

Revision ID: 0014_line_level_booking_dates
Revises: 0013_booking_person
Create Date: 2026-06-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_line_level_booking_dates"
down_revision: str | None = "0013_booking_person"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "booking_lines",
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("booking_lines", sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "basket_lines",
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("basket_lines", sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True))

    op.execute(
        """
        UPDATE booking_lines AS bl
        SET starts_at = b.starts_at,
            ends_at = b.ends_at
        FROM bookings AS b
        WHERE bl.booking_id = b.id
        """
    )
    op.execute(
        """
        UPDATE basket_lines AS bl
        SET starts_at = b.starts_at,
            ends_at = b.ends_at
        FROM baskets AS b
        WHERE bl.basket_id = b.id
        """
    )

    op.alter_column("booking_lines", "starts_at", nullable=False)
    op.alter_column("booking_lines", "ends_at", nullable=False)
    op.alter_column("basket_lines", "starts_at", nullable=False)
    op.alter_column("basket_lines", "ends_at", nullable=False)

    op.drop_constraint(op.f("uq_booking_lines_booking_id"), "booking_lines", type_="unique")
    op.drop_constraint(op.f("uq_basket_lines_basket_id"), "basket_lines", type_="unique")
    op.create_unique_constraint(
        op.f("uq_booking_lines_booking_id"),
        "booking_lines",
        ["booking_id", "asset_id", "location_id", "starts_at", "ends_at"],
    )
    op.create_unique_constraint(
        op.f("uq_basket_lines_basket_id"),
        "basket_lines",
        ["basket_id", "asset_id", "location_id", "starts_at", "ends_at"],
    )
    op.create_check_constraint(
        op.f("ck_booking_lines_booking_line_valid_time_range"),
        "booking_lines",
        "starts_at < ends_at",
    )
    op.create_check_constraint(
        op.f("ck_basket_lines_basket_line_valid_time_range"),
        "basket_lines",
        "starts_at < ends_at",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_basket_lines_basket_line_valid_time_range"),
        "basket_lines",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_booking_lines_booking_line_valid_time_range"),
        "booking_lines",
        type_="check",
    )
    op.drop_constraint(op.f("uq_basket_lines_basket_id"), "basket_lines", type_="unique")
    op.drop_constraint(op.f("uq_booking_lines_booking_id"), "booking_lines", type_="unique")
    op.create_unique_constraint(
        op.f("uq_basket_lines_basket_id"),
        "basket_lines",
        ["basket_id", "asset_id", "location_id"],
    )
    op.create_unique_constraint(
        op.f("uq_booking_lines_booking_id"),
        "booking_lines",
        ["booking_id", "asset_id", "location_id"],
    )
    op.drop_column("basket_lines", "ends_at")
    op.drop_column("basket_lines", "starts_at")
    op.drop_column("booking_lines", "ends_at")
    op.drop_column("booking_lines", "starts_at")
