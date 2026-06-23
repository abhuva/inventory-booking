"""Add asset description.

Revision ID: 0008_asset_description
Revises: 0007_asset_images
Create Date: 2026-06-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_asset_description"
down_revision: str | None = "0007_asset_images"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("assets", sa.Column("description", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("assets", "description")
