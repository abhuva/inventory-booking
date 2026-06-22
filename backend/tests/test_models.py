from inventory_booking_api.models import Base


def test_initial_domain_tables_are_registered() -> None:
    expected_tables = {
        "assets",
        "audit_logs",
        "categories",
        "item_events",
        "locations",
        "stock_levels",
        "users",
    }

    assert expected_tables.issubset(Base.metadata.tables.keys())


def test_asset_type_check_constraint_is_registered() -> None:
    asset_table = Base.metadata.tables["assets"]

    constraint_names = {constraint.name for constraint in asset_table.constraints}

    assert "ck_assets_asset_type_unit_name_consistency" in constraint_names


def test_stock_level_asset_location_uniqueness_is_registered() -> None:
    stock_level_table = Base.metadata.tables["stock_levels"]

    constraint_names = {constraint.name for constraint in stock_level_table.constraints}

    assert "uq_stock_levels_asset_location" in constraint_names


def test_main_import_registers_all_foreign_key_targets() -> None:
    import inventory_booking_api.main  # noqa: F401

    assets_table = Base.metadata.tables["assets"]

    for foreign_key in assets_table.foreign_keys:
        assert foreign_key.column.table.name in Base.metadata.tables
