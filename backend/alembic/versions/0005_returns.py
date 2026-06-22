"""Add returns.

Revision ID: 0005_returns
Revises: 0004_checkouts
Create Date: 2026-06-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_returns"
down_revision: str | None = "0004_checkouts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
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
        "returns",
        sa.Column("checkout_id", sa.Uuid(), nullable=False),
        sa.Column("returned_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["checkout_id"], ["checkouts.id"], name=op.f("fk_returns_checkout_id_checkouts")
        ),
        sa.ForeignKeyConstraint(
            ["returned_by_user_id"],
            ["users.id"],
            name=op.f("fk_returns_returned_by_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_returns")),
    )
    op.create_index(op.f("ix_returns_checkout_id"), "returns", ["checkout_id"])

    op.create_table(
        "return_lines",
        sa.Column("return_id", sa.Uuid(), nullable=False),
        sa.Column("checkout_line_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("condition_in", asset_condition, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "quantity IS NULL OR quantity > 0",
            name=op.f("ck_return_lines_return_line_positive_quantity"),
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"], ["assets.id"], name=op.f("fk_return_lines_asset_id_assets")
        ),
        sa.ForeignKeyConstraint(
            ["checkout_line_id"],
            ["checkout_lines.id"],
            name=op.f("fk_return_lines_checkout_line_id_checkout_lines"),
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.id"],
            name=op.f("fk_return_lines_location_id_locations"),
        ),
        sa.ForeignKeyConstraint(
            ["return_id"], ["returns.id"], name=op.f("fk_return_lines_return_id_returns")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_return_lines")),
    )
    op.create_index(op.f("ix_return_lines_checkout_line_id"), "return_lines", ["checkout_line_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_return_lines_checkout_line_id"), table_name="return_lines")
    op.drop_table("return_lines")
    op.drop_index(op.f("ix_returns_checkout_id"), table_name="returns")
    op.drop_table("returns")
