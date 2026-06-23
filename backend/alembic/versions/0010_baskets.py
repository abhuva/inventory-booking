"""Add temporary reservation baskets.

Revision ID: 0010_baskets
Revises: 0009_inventory_option_c
Create Date: 2026-06-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_baskets"
down_revision: str | None = "0009_inventory_option_c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    basket_status = postgresql.ENUM(
        "active",
        "confirmed",
        "cancelled",
        "expired",
        name="basket_status",
        create_type=False,
    )
    basket_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "baskets",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("status", basket_status, nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("starts_at < ends_at", name=op.f("ck_baskets_basket_valid_time_range")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_baskets_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_baskets")),
    )
    op.create_index(op.f("ix_baskets_user_id"), "baskets", ["user_id"])
    op.create_index(op.f("ix_baskets_status"), "baskets", ["status"])
    op.create_index(op.f("ix_baskets_expires_at"), "baskets", ["expires_at"])

    op.create_table(
        "basket_lines",
        sa.Column("basket_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "quantity IS NULL OR quantity > 0",
            name=op.f("ck_basket_lines_basket_line_positive_quantity"),
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"], ["assets.id"], name=op.f("fk_basket_lines_asset_id_assets")
        ),
        sa.ForeignKeyConstraint(
            ["basket_id"], ["baskets.id"], name=op.f("fk_basket_lines_basket_id_baskets")
        ),
        sa.ForeignKeyConstraint(
            ["location_id"], ["locations.id"], name=op.f("fk_basket_lines_location_id_locations")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_basket_lines")),
        sa.UniqueConstraint(
            "basket_id",
            "asset_id",
            "location_id",
            name=op.f("uq_basket_lines_basket_id"),
        ),
    )
    op.create_index(op.f("ix_basket_lines_asset_id"), "basket_lines", ["asset_id"])
    op.create_index(op.f("ix_basket_lines_basket_id"), "basket_lines", ["basket_id"])
    op.create_index(op.f("ix_basket_lines_location_id"), "basket_lines", ["location_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_basket_lines_location_id"), table_name="basket_lines")
    op.drop_index(op.f("ix_basket_lines_basket_id"), table_name="basket_lines")
    op.drop_index(op.f("ix_basket_lines_asset_id"), table_name="basket_lines")
    op.drop_table("basket_lines")
    op.drop_index(op.f("ix_baskets_expires_at"), table_name="baskets")
    op.drop_index(op.f("ix_baskets_status"), table_name="baskets")
    op.drop_index(op.f("ix_baskets_user_id"), table_name="baskets")
    op.drop_table("baskets")
    postgresql.ENUM(name="basket_status").drop(op.get_bind(), checkfirst=True)
