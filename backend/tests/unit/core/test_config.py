"""Unit tests for docmind/core/config.py."""
from docmind.core.config import Settings, get_settings


class TestSettings:
    """Tests for the Settings class."""

    def test_default_app_name(self):
        s = Settings()
        assert s.APP_NAME == "DocMind-VLM"

    def test_default_vlm_provider(self):
        s = Settings()
        assert s.VLM_PROVIDER == "openrouter"

    def test_database_url_property(self):
        s = Settings(DB_USER="u", DB_PASSWORD="p", DB_HOST="h", DB_PORT=5432, DB_NAME="d")
        assert s.database_url == "postgresql+asyncpg://u:p@h:5432/d"

    def test_allowed_origins_splits_csv(self):
        s = Settings(ALLOWED_ORIGINS_STR="http://a.com, http://b.com")
        assert s.allowed_origins == ["http://a.com", "http://b.com"]

    def test_port_is_integer(self):
        s = Settings()
        assert isinstance(s.APP_PORT, int)


class TestGetSettings:
    """Tests for the get_settings cached function."""

    def test_returns_settings_instance(self):
        result = get_settings()
        assert isinstance(result, Settings)

    def test_returns_same_instance(self):
        a = get_settings()
        b = get_settings()
        assert a is b
