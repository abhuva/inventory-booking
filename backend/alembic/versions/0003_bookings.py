"""Add bookings.

Revision ID: 0003_bookings
Revises: 0002_user_sessions
Create Date: 2026-06-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_bookings"
down_revision: str | None = "0002_user_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    booking_status = postgresql.ENUM(
        "reserved",
        "cancelled",
        "checked_out",
        "completed",
        name="booking_status",
        create_type=False,
    )
    booking_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "bookings",
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("status", booking_status, nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "starts_at < ends_at",
            name=op.f("ck_bookings_booking_valid_time_range"),
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_user_id"],
            ["users.id"],
            name=op.f("fk_bookings_requested_by_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bookings")),
    )
    op.create_index(op.f("ix_bookings_starts_at"), "bookings", ["starts_at"])
    op.create_index(op.f("ix_bookings_ends_at"), "bookings", ["ends_at"])
    op.create_index(op.f("ix_bookings_status"), "bookings", ["status"])

    op.create_table(
        "booking_lines",
        sa.Column("booking_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "quantity IS NULL OR quantity > 0",
            name=op.f("ck_booking_lines_booking_line_positive_quantity"),
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"], ["assets.id"], name=op.f("fk_booking_lines_asset_id_assets")
        ),
        sa.ForeignKeyConstraint(
            ["booking_id"], ["bookings.id"], name=op.f("fk_booking_lines_booking_id_bookings")
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.id"],
            name=op.f("fk_booking_lines_location_id_locations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_booking_lines")),
        sa.UniqueConstraint(
            "booking_id",
            "asset_id",
            "location_id",
            name=op.f("uq_booking_lines_booking_id"),
        ),
    )
    op.create_index(op.f("ix_booking_lines_asset_id"), "booking_lines", ["asset_id"])
    op.create_index(op.f("ix_booking_lines_location_id"), "booking_lines", ["location_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_booking_lines_location_id"), table_name="booking_lines")
    op.drop_index(op.f("ix_booking_lines_asset_id"), table_name="booking_lines")
    op.drop_table("booking_lines")
    op.drop_index(op.f("ix_bookings_status"), table_name="bookings")
    op.drop_index(op.f("ix_bookings_ends_at"), table_name="bookings")
    op.drop_index(op.f("ix_bookings_starts_at"), table_name="bookings")
    op.drop_table("bookings")
    postgresql.ENUM(name="booking_status").drop(op.get_bind(), checkfirst=True)
