from app.config import settings

def test_settings_load():
    assert settings.burgerprints_api_key == "147a7d53-f1ed-0203-e065-00b14e8ebbf6"
    assert settings.burgerprints_enable_sandbox_create_order is True
    assert settings.supabase_db_url is not None
    assert len(settings.supabase_db_url) > 0
