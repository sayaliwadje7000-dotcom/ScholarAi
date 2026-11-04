import pytest

from app.core.retry_config import (
    DocumentRetrySettings,
    load_document_retry_settings,
)


def test_default_retry_configuration(monkeypatch):

    monkeypatch.delenv(
        "DOCUMENT_RETRY_ENABLED",
        raising=False,
    )

    monkeypatch.delenv(
        "DOCUMENT_MAX_PROCESSING_ATTEMPTS",
        raising=False,
    )

    monkeypatch.delenv(
        "DOCUMENT_RETRY_INITIAL_DELAY_SECONDS",
        raising=False,
    )

    monkeypatch.delenv(
        "DOCUMENT_RETRY_BACKOFF_MULTIPLIER",
        raising=False,
    )

    monkeypatch.delenv(
        "DOCUMENT_RETRY_MAX_DELAY_SECONDS",
        raising=False,
    )

    settings = load_document_retry_settings()

    assert settings.enabled is True
    assert settings.max_attempts == 3
    assert settings.initial_delay_seconds == 5.0
    assert settings.backoff_multiplier == 2.0
    assert settings.max_delay_seconds == 60.0


def test_custom_retry_configuration(monkeypatch):

    monkeypatch.setenv("DOCUMENT_RETRY_ENABLED", "true")
    monkeypatch.setenv("DOCUMENT_MAX_PROCESSING_ATTEMPTS", "5")
    monkeypatch.setenv("DOCUMENT_RETRY_INITIAL_DELAY_SECONDS", "3")
    monkeypatch.setenv("DOCUMENT_RETRY_BACKOFF_MULTIPLIER", "3")
    monkeypatch.setenv("DOCUMENT_RETRY_MAX_DELAY_SECONDS", "30")

    settings = load_document_retry_settings()

    assert settings.max_attempts == 5
    assert settings.initial_delay_seconds == 3.0
    assert settings.backoff_multiplier == 3.0
    assert settings.max_delay_seconds == 30.0


def test_rejects_zero_max_attempts(monkeypatch):

    monkeypatch.setenv(
        "DOCUMENT_MAX_PROCESSING_ATTEMPTS",
        "0",
    )

    with pytest.raises(ValueError):
        load_document_retry_settings()


def test_rejects_invalid_backoff_multiplier(monkeypatch):

    monkeypatch.setenv(
        "DOCUMENT_RETRY_BACKOFF_MULTIPLIER",
        "0.5",
    )

    with pytest.raises(ValueError):
        load_document_retry_settings()


def test_rejects_max_delay_smaller_than_initial_delay(monkeypatch):

    monkeypatch.setenv(
        "DOCUMENT_RETRY_INITIAL_DELAY_SECONDS",
        "20",
    )

    monkeypatch.setenv(
        "DOCUMENT_RETRY_MAX_DELAY_SECONDS",
        "10",
    )

    with pytest.raises(ValueError):
        load_document_retry_settings()


def test_rejects_infinite_delay(monkeypatch):

    monkeypatch.setenv(
        "DOCUMENT_RETRY_INITIAL_DELAY_SECONDS",
        "inf",
    )

    with pytest.raises(ValueError):
        load_document_retry_settings()