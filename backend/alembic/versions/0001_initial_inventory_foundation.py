"""Initial inventory foundation.

Revision ID: 0001_inventory_base
Revises:
Create Date: 2026-06-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_inventory_base"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    user_role = postgresql.ENUM("admin", "user", name="user_role", create_type=False)
    location_type = postgresql.ENUM(
        "room",
        "storage",
        "vehicle",
        "project_site",
        "external_space",
        "person_home",
        "repair",
        "unknown",
        name="location_type",
        create_type=False,
    )
    asset_type = postgresql.ENUM("tracked", "stock", name="asset_type", create_type=False)
    asset_status = postgresql.ENUM(
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
    asset_condition = postgresql.ENUM(
        "unknown",
        "good",
        "worn",
        "damaged",
        "needs_repair",
        name="asset_condition",
        create_type=False,
    )
    item_event_type = postgresql.ENUM(
        "created",
        "updated",
        "qr_assigned",
        "moved",
        "reserved",
        "checked_out",
        "returned",
        "maintenance_started",
        "maintenance_completed",
        "damaged",
        "lost",
        "found",
        "retired",
        name="item_event_type",
        create_type=False,
    )
    audit_action = postgresql.ENUM(
        "create",
        "update",
        "delete",
        "login",
        "logout",
        "override",
        name="audit_action",
        create_type=False,
    )

    user_role.create(op.get_bind(), checkfirst=True)
    location_type.create(op.get_bind(), checkfirst=True)
    asset_type.create(op.get_bind(), checkfirst=True)
    asset_status.create(op.get_bind(), checkfirst=True)
    asset_condition.create(op.get_bind(), checkfirst=True)
    item_event_type.create(op.get_bind(), checkfirst=True)
    audit_action.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)

    op.create_table(
        "categories",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categories")),
        sa.UniqueConstraint("name", name=op.f("uq_categories_name")),
    )
    op.create_index(op.f("ix_categories_name"), "categories", ["name"], unique=False)

    op.create_table(
        "locations",
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("type", location_type, nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("responsible_user_id", sa.Uuid(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["responsible_user_id"],
            ["users.id"],
            name=op.f("fk_locations_responsible_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_locations")),
        sa.UniqueConstraint("name", name=op.f("uq_locations_name")),
    )
    op.create_index(op.f("ix_locations_name"), "locations", ["name"], unique=False)

    op.create_table(
        "assets",
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("asset_type", asset_type, nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("status", asset_status, nullable=False),
        sa.Column("condition", asset_condition, nullable=False),
        sa.Column("unit_name", sa.String(length=40), nullable=True),
        sa.Column("home_location_id", sa.Uuid(), nullable=True),
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
        sa.CheckConstraint(
            "(asset_type = 'tracked' AND unit_name IS NULL) OR "
            "(asset_type = 'stock' AND unit_name IS NOT NULL)",
            name=op.f("ck_assets_asset_type_unit_name_consistency"),
        ),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"], name=op.f("fk_assets_category_id_categories")
        ),
        sa.ForeignKeyConstraint(
            ["current_holder_user_id"],
            ["users.id"],
            name=op.f("fk_assets_current_holder_user_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["current_location_id"],
            ["locations.id"],
            name=op.f("fk_assets_current_location_id_locations"),
        ),
        sa.ForeignKeyConstraint(
            ["home_location_id"],
            ["locations.id"],
            name=op.f("fk_assets_home_location_id_locations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assets")),
        sa.UniqueConstraint("asset_tag", name=op.f("uq_assets_asset_tag")),
    )
    op.create_index(op.f("ix_assets_name"), "assets", ["name"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", audit_action, nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("summary", sa.String(length=240), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["users.id"], name=op.f("fk_audit_logs_actor_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )

    op.create_table(
        "item_events",
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", item_event_type, nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("from_location_id", sa.Uuid(), nullable=True),
        sa.Column("to_location_id", sa.Uuid(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["users.id"], name=op.f("fk_item_events_actor_user_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"], ["assets.id"], name=op.f("fk_item_events_asset_id_assets")
        ),
        sa.ForeignKeyConstraint(
            ["from_location_id"],
            ["locations.id"],
            name=op.f("fk_item_events_from_location_id_locations"),
        ),
        sa.ForeignKeyConstraint(
            ["to_location_id"],
            ["locations.id"],
            name=op.f("fk_item_events_to_location_id_locations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_item_events")),
    )
    op.create_index(op.f("ix_item_events_asset_id"), "item_events", ["asset_id"], unique=False)

    op.create_table(
        "stock_levels",
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=False),
        sa.Column("quantity_total", sa.Integer(), nullable=False),
        sa.Column("quantity_reserved", sa.Integer(), nullable=False),
        sa.Column("quantity_checked_out", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "quantity_checked_out >= 0",
            name=op.f("ck_stock_levels_stock_level_quantity_checked_out_non_negative"),
        ),
        sa.CheckConstraint(
            "quantity_reserved >= 0",
            name=op.f("ck_stock_levels_stock_level_quantity_reserved_non_negative"),
        ),
        sa.CheckConstraint(
            "quantity_total >= 0",
            name=op.f("ck_stock_levels_stock_level_quantity_total_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"], ["assets.id"], name=op.f("fk_stock_levels_asset_id_assets")
        ),
        sa.ForeignKeyConstraint(
            ["location_id"], ["locations.id"], name=op.f("fk_stock_levels_location_id_locations")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stock_levels")),
        sa.UniqueConstraint("asset_id", "location_id", name="uq_stock_levels_asset_location"),
    )


def downgrade() -> None:
    op.drop_table("stock_levels")
    op.drop_index(op.f("ix_item_events_asset_id"), table_name="item_events")
    op.drop_table("item_events")
    op.drop_table("audit_logs")
    op.drop_index(op.f("ix_assets_name"), table_name="assets")
    op.drop_table("assets")
    op.drop_index(op.f("ix_locations_name"), table_name="locations")
    op.drop_table("locations")
    op.drop_index(op.f("ix_categories_name"), table_name="categories")
    op.drop_table("categories")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    for enum_name in (
        "audit_action",
        "item_event_type",
        "asset_condition",
        "asset_status",
        "asset_type",
        "location_type",
        "user_role",
    ):
        postgresql.ENUM(name=enum_name).drop(op.get_bind(), checkfirst=True)
