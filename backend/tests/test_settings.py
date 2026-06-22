from inventory_booking_api.settings import Settings


def test_cors_origins_are_split_and_normalized() -> None:
    settings = Settings(cors_origins="http://localhost:5173/, http://127.0.0.1:5173")

    assert settings.cors_origin_list == ["http://localhost:5173", "http://127.0.0.1:5173"]
