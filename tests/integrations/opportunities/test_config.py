import pytest

from app.core.opportunity_provider_config import (
    OpportunityProviderSettings,
)


def test_default_opportunity_settings_are_disabled():

    settings = OpportunityProviderSettings()

    assert settings.enabled is False

    assert settings.adzuna_enabled is False

    assert settings.adzuna_configured is False


def test_adzuna_credentials_are_detected():

    settings = OpportunityProviderSettings(
        adzuna_app_id="test-id",
        adzuna_app_key="test-key",
    )

    assert settings.adzuna_configured is True


def test_invalid_timeout_is_rejected():

    with pytest.raises(ValueError):

        OpportunityProviderSettings(
            timeout_seconds=0,
        )


def test_invalid_retry_count_is_rejected():

    with pytest.raises(ValueError):

        OpportunityProviderSettings(
            max_retries=-1,
        )


def test_invalid_country_code_is_rejected():

    with pytest.raises(ValueError):

        OpportunityProviderSettings(
            adzuna_country="india",
        )


def test_invalid_result_limit_is_rejected():

    with pytest.raises(ValueError):

        OpportunityProviderSettings(
            max_results_per_provider=100,
        )