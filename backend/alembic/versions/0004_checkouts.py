"""Add checkouts.

Revision ID: 0004_checkouts
Revises: 0003_bookings
Create Date: 2026-06-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_checkouts"
down_revision: str | None = "0003_bookings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    checkout_status = postgresql.ENUM(
        "checked_out",
        "partially_returned",
        "returned",
        name="checkout_status",
        create_type=False,
    )
    checkout_status.create(op.get_bind(), checkfirst=True)
    asset_condition = postgresql.ENUM(
        "unknown",
        "good",
        "worn",
        "damaged",
        "needs_repair",
        name="asset_condition",
        create_type=False,
    )

    op.create_table(
        "checkouts",
        sa.Column("booking_id", sa.Uuid(), nullable=False),
        sa.Column("checked_out_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("checked_out_to_user_id", sa.Uuid(), nullable=True),
        sa.Column("status", checkout_status, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["booking_id"], ["bookings.id"], name=op.f("fk_checkouts_booking_id_bookings")
        ),
        sa.ForeignKeyConstraint(
            ["checked_out_by_user_id"],
            ["users.id"],
            name=op.f("fk_checkouts_checked_out_by_user_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["checked_out_to_user_id"],
            ["users.id"],
            name=op.f("fk_checkouts_checked_out_to_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_checkouts")),
        sa.UniqueConstraint("booking_id", name=op.f("uq_checkouts_booking_id")),
    )

    op.create_table(
        "checkout_lines",
        sa.Column("checkout_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("quantity_returned", sa.Integer(), nullable=False),
        sa.Column("condition_out", asset_condition, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "quantity IS NULL OR quantity > 0",
            name=op.f("ck_checkout_lines_checkout_line_positive_quantity"),
        ),
        sa.CheckConstraint(
            "quantity_returned >= 0",
            name=op.f("ck_checkout_lines_checkout_line_returned_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"], ["assets.id"], name=op.f("fk_checkout_lines_asset_id_assets")
        ),
        sa.ForeignKeyConstraint(
            ["checkout_id"], ["checkouts.id"], name=op.f("fk_checkout_lines_checkout_id_checkouts")
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.id"],
            name=op.f("fk_checkout_lines_location_id_locations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_checkout_lines")),
        sa.UniqueConstraint(
            "checkout_id",
            "asset_id",
            "location_id",
            name=op.f("uq_checkout_lines_checkout_id"),
        ),
    )
    op.create_index(op.f("ix_checkout_lines_asset_id"), "checkout_lines", ["asset_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_checkout_lines_asset_id"), table_name="checkout_lines")
    op.drop_table("checkout_lines")
    op.drop_table("checkouts")
    postgresql.ENUM(name="checkout_status").drop(op.get_bind(), checkfirst=True)
