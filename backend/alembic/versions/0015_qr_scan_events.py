"""Add user-scoped QR scan notification events.

Revision ID: 0015_qr_scan_events
Revises: 0014_line_level_booking_dates
Create Date: 2026-08-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_qr_scan_events"
down_revision: str | None = "0014_line_level_booking_dates"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "qr_scan_events",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("qr_code_id", sa.Uuid(), nullable=False),
        sa.Column("client_event_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
            name=op.f("fk_qr_scan_events_asset_id_assets"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["qr_code_id"],
            ["qr_codes.id"],
            name=op.f("fk_qr_scan_events_qr_code_id_qr_codes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_qr_scan_events_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_qr_scan_events")),
        sa.UniqueConstraint(
            "user_id", "client_event_id", name="uq_qr_scan_events_user_client_event"
        ),
    )
    op.create_index(
        "ix_qr_scan_events_user_created_at",
        "qr_scan_events",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_qr_scan_events_user_created_at", table_name="qr_scan_events")
    op.drop_table("qr_scan_events")
