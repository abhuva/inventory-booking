"""Add physical inventory state tables.

Revision ID: 0009_inventory_option_c
Revises: 0008_asset_description
Create Date: 2026-06-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_inventory_option_c"
down_revision: str | None = "0008_asset_description"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

asset_status_enum = postgresql.ENUM(
    "available",
    "reserved",
    "checked_out",
    "in_transfer",
    "maintenance",
    "damaged",
    "lost",
    "retired",
    name="asset_status",
    create_type=False,
)
asset_condition_enum = postgresql.ENUM(
    "unknown",
    "good",
    "worn",
    "damaged",
    "needs_repair",
    name="asset_condition",
    create_type=False,
)


def upgrade() -> None:
    op.create_table(
        "tracked_units",
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(length=180), nullable=True),
        sa.Column("status", asset_status_enum, nullable=False),
        sa.Column("condition", asset_condition_enum, nullable=False),
        sa.Column("current_location_id", sa.Uuid(), nullable=True),
        sa.Column("current_holder_user_id", sa.Uuid(), nullable=True),
        sa.Column("manufacturer", sa.String(length=120), nullable=True),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("serial_number", sa.String(length=120), nullable=True),
        sa.Column("asset_tag", sa.String(length=80), nullable=True),
        sa.Column("replacement_value", sa.Numeric(12, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
            name=op.f("fk_tracked_units_asset_id_assets"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["current_holder_user_id"],
            ["users.id"],
            name=op.f("fk_tracked_units_current_holder_user_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["current_location_id"],
            ["locations.id"],
            name=op.f("fk_tracked_units_current_location_id_locations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tracked_units")),
        sa.UniqueConstraint("asset_tag", name=op.f("uq_tracked_units_asset_tag")),
    )
    op.create_index(op.f("ix_tracked_units_asset_id"), "tracked_units", ["asset_id"])

    op.create_table(
        "stock_batches",
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=True),
        sa.Column("holder_user_id", sa.Uuid(), nullable=True),
        sa.Column("checkout_line_id", sa.Uuid(), nullable=True),
        sa.Column("status", asset_status_enum, nullable=False),
        sa.Column("condition", asset_condition_enum, nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "quantity > 0",
            name=op.f("ck_stock_batches_stock_batch_quantity_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
            name=op.f("fk_stock_batches_asset_id_assets"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["holder_user_id"], ["users.id"], name=op.f("fk_stock_batches_holder_user_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["checkout_line_id"],
            ["checkout_lines.id"],
            name=op.f("fk_stock_batches_checkout_line_id_checkout_lines"),
        ),
        sa.ForeignKeyConstraint(
            ["location_id"], ["locations.id"], name=op.f("fk_stock_batches_location_id_locations")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stock_batches")),
    )
    op.create_index(op.f("ix_stock_batches_asset_id"), "stock_batches", ["asset_id"])

    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            INSERT INTO tracked_units (
                id,
                asset_id,
                label,
                status,
                condition,
                current_location_id,
                current_holder_user_id,
                manufacturer,
                model,
                serial_number,
                asset_tag,
                replacement_value,
                notes,
                created_at,
                updated_at
            )
            SELECT
                gen_random_uuid(),
                id,
                name,
                status,
                condition,
                current_location_id,
                current_holder_user_id,
                manufacturer,
                model,
                serial_number,
                asset_tag,
                replacement_value,
                notes,
                created_at,
                updated_at
            FROM assets
            WHERE asset_type = 'tracked'
            """
        )
    )
    bind.execute(
        sa.text(
            """
            INSERT INTO stock_batches (
                id,
                asset_id,
                location_id,
                holder_user_id,
                checkout_line_id,
                status,
                condition,
                quantity,
                notes,
                created_at,
                updated_at
            )
            SELECT
                gen_random_uuid(),
                asset_id,
                location_id,
                NULL,
                NULL,
                'available'::asset_status,
                'unknown'::asset_condition,
                quantity_total - quantity_checked_out,
                NULL,
                created_at,
                updated_at
            FROM stock_levels
            WHERE quantity_total - quantity_checked_out > 0
            """
        )
    )
    bind.execute(
        sa.text(
            """
            INSERT INTO stock_batches (
                id,
                asset_id,
                location_id,
                holder_user_id,
                checkout_line_id,
                status,
                condition,
                quantity,
                notes,
                created_at,
                updated_at
            )
            SELECT
                gen_random_uuid(),
                asset_id,
                location_id,
                NULL,
                NULL,
                'checked_out'::asset_status,
                'unknown'::asset_condition,
                quantity_checked_out,
                'Migrated checked-out stock quantity',
                created_at,
                updated_at
            FROM stock_levels
            WHERE quantity_checked_out > 0
            """
        )
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_stock_batches_asset_id"), table_name="stock_batches")
    op.drop_table("stock_batches")
    op.drop_index(op.f("ix_tracked_units_asset_id"), table_name="tracked_units")
    op.drop_table("tracked_units")
