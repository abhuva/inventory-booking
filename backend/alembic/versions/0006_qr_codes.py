"""Add QR codes.

Revision ID: 0006_qr_codes
Revises: 0005_returns
Create Date: 2026-06-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_qr_codes"
down_revision: str | None = "0005_returns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "qr_codes",
        sa.Column("token", sa.String(length=80), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=True),
        sa.Column("label", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["asset_id"], ["assets.id"], name=op.f("fk_qr_codes_asset_id_assets")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_qr_codes")),
        sa.UniqueConstraint("asset_id", name=op.f("uq_qr_codes_asset_id")),
        sa.UniqueConstraint("token", name=op.f("uq_qr_codes_token")),
    )
    op.create_index(op.f("ix_qr_codes_token"), "qr_codes", ["token"])


def downgrade() -> None:
    op.drop_index(op.f("ix_qr_codes_token"), table_name="qr_codes")
    op.drop_table("qr_codes")
