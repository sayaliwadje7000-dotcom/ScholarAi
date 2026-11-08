import pytest

from app.services.recommendations.ml.privacy.privacy_config import (
    PrivacyConfig,
)


def test_default_privacy_configuration():

    config = PrivacyConfig()

    assert config.reject_identifier_features is True

    assert config.reject_sensitive_features is True

    assert config.reject_target_leakage is True

    assert config.require_user_separated_validation is True

    assert config.redact_pii_from_metadata is True


def test_invalid_minimum_dataset_size():

    with pytest.raises(ValueError):

        PrivacyConfig(
            minimum_dataset_samples=0
        )


def test_invalid_minimum_distinct_users():

    with pytest.raises(ValueError):

        PrivacyConfig(
            minimum_distinct_users=1
        )


def test_invalid_metadata_length():

    with pytest.raises(ValueError):

        PrivacyConfig(
            maximum_metadata_string_length=0
        )