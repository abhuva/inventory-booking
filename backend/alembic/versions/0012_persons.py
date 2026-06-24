"""Add persons and location responsible person.

Revision ID: 0012_persons
Revises: 0011_location_images
Create Date: 2026-06-23
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_persons"
down_revision: str | None = "0011_location_images"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    person_type = postgresql.ENUM(
        "admin",
        "user",
        "team",
        "external",
        name="person_type",
        create_type=False,
    )
    person_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "persons",
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("person_type", person_type, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=80), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_persons_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_persons")),
        sa.UniqueConstraint("user_id", name=op.f("uq_persons_user_id")),
    )
    op.create_index(op.f("ix_persons_display_name"), "persons", ["display_name"])

    op.add_column("locations", sa.Column("responsible_person_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_locations_responsible_person_id_persons"),
        "locations",
        "persons",
        ["responsible_person_id"],
        ["id"],
    )

    bind = op.get_bind()
    now = datetime.now(UTC)
    users = bind.execute(
        sa.text("SELECT id, email, display_name, role, is_active FROM users")
    ).mappings()
    user_person_ids: dict[str, str] = {}
    for user in users:
        person_id = uuid4()
        user_person_ids[str(user["id"])] = str(person_id)
        bind.execute(
            sa.text(
                """
                INSERT INTO persons (
                    id, display_name, person_type, email, user_id, is_active, created_at, updated_at
                ) VALUES (
                    :id,
                    :display_name,
                    :person_type,
                    :email,
                    :user_id,
                    :is_active,
                    :created_at,
                    :updated_at
                )
                """
            ),
            {
                "id": person_id,
                "display_name": user["display_name"],
                "person_type": user["role"],
                "email": user["email"],
                "user_id": user["id"],
                "is_active": user["is_active"],
                "created_at": now,
                "updated_at": now,
            },
        )

    for user_id, person_id in user_person_ids.items():
        bind.execute(
            sa.text(
                """
                UPDATE locations
                SET responsible_person_id = :person_id
                WHERE responsible_user_id = :user_id
                """
            ),
            {"person_id": person_id, "user_id": user_id},
        )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_locations_responsible_person_id_persons"), "locations", type_="foreignkey"
    )
    op.drop_column("locations", "responsible_person_id")
    op.drop_index(op.f("ix_persons_display_name"), table_name="persons")
    op.drop_table("persons")
    postgresql.ENUM(name="person_type").drop(op.get_bind(), checkfirst=True)
