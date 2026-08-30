"""Add asset rental pricing and booking-line price snapshots.

Revision ID: 0016_rental_pricing
Revises: 0015_qr_scan_events
Create Date: 2026-08-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_rental_pricing"
down_revision: str | None = "0015_qr_scan_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("assets", sa.Column("rental_recoup_days", sa.Integer(), nullable=True))
    op.add_column(
        "assets",
        sa.Column("rental_maintenance_cost_per_day", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "assets",
        sa.Column("rental_profit_margin_percent", sa.Numeric(7, 2), nullable=True),
    )
    op.create_check_constraint(
        op.f("ck_assets_rental_recoup_days_positive"),
        "assets",
        "rental_recoup_days IS NULL OR rental_recoup_days > 0",
    )
    op.create_check_constraint(
        op.f("ck_assets_rental_maintenance_cost_non_negative"),
        "assets",
        "rental_maintenance_cost_per_day IS NULL OR rental_maintenance_cost_per_day >= 0",
    )
    op.create_check_constraint(
        op.f("ck_assets_rental_profit_margin_non_negative"),
        "assets",
        "rental_profit_margin_percent IS NULL OR rental_profit_margin_percent >= 0",
    )

    op.add_column(
        "booking_lines",
        sa.Column("rental_unit_price_per_day", sa.Numeric(14, 6), nullable=True),
    )
    op.add_column("booking_lines", sa.Column("rental_days", sa.Integer(), nullable=True))
    op.add_column(
        "booking_lines",
        sa.Column("rental_total", sa.Numeric(14, 2), nullable=True),
    )
    op.create_check_constraint(
        op.f("ck_booking_lines_rental_unit_price_non_negative"),
        "booking_lines",
        "rental_unit_price_per_day IS NULL OR rental_unit_price_per_day >= 0",
    )
    op.create_check_constraint(
        op.f("ck_booking_lines_rental_days_positive"),
        "booking_lines",
        "rental_days IS NULL OR rental_days > 0",
    )
    op.create_check_constraint(
        op.f("ck_booking_lines_rental_total_non_negative"),
        "booking_lines",
        "rental_total IS NULL OR rental_total >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_booking_lines_rental_total_non_negative"),
        "booking_lines",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_booking_lines_rental_days_positive"),
        "booking_lines",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_booking_lines_rental_unit_price_non_negative"),
        "booking_lines",
        type_="check",
    )
    op.drop_column("booking_lines", "rental_total")
    op.drop_column("booking_lines", "rental_days")
    op.drop_column("booking_lines", "rental_unit_price_per_day")

    op.drop_constraint(
        op.f("ck_assets_rental_profit_margin_non_negative"), "assets", type_="check"
    )
    op.drop_constraint(
        op.f("ck_assets_rental_maintenance_cost_non_negative"), "assets", type_="check"
    )
    op.drop_constraint(op.f("ck_assets_rental_recoup_days_positive"), "assets", type_="check")
    op.drop_column("assets", "rental_profit_margin_percent")
    op.drop_column("assets", "rental_maintenance_cost_per_day")
    op.drop_column("assets", "rental_recoup_days")
