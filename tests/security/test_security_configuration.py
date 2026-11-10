"""Phase 18.11: environment-backed security configuration validation."""

import pytest

from app.core.security_config import SecuritySettings


def test_security_settings_load_valid_environment(monkeypatch):
    monkeypatch.setenv("SCHOLARAI_RATE_LIMIT_ENABLED", "false")
    monkeypatch.setenv("SCHOLARAI_RATE_LIMIT_WINDOW_SECONDS", "30")
    monkeypatch.setenv("SCHOLARAI_API_RATE_LIMIT", "75")
    monkeypatch.setenv("SCHOLARAI_LOGIN_RATE_LIMIT", "4")
    settings = SecuritySettings.from_environment()
    assert settings.rate_limit_enabled is False
    assert settings.rate_limit_window_seconds == 30
    assert settings.api_requests_per_window == 75
    assert settings.login_requests_per_window == 4


@pytest.mark.parametrize("value", ["0", "-1", "not-an-integer", "999999999"])
def test_rejects_invalid_api_rate_limit(monkeypatch, value):
    monkeypatch.setenv("SCHOLARAI_API_RATE_LIMIT", value)
    with pytest.raises(ValueError):
        SecuritySettings.from_environment()


@pytest.mark.parametrize("value", ["maybe", "2", ""])
def test_rejects_invalid_boolean(monkeypatch, value):
    monkeypatch.setenv("SCHOLARAI_RATE_LIMIT_ENABLED", value)
    with pytest.raises(ValueError):
        SecuritySettings.from_environment()
