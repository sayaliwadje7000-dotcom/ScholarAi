from app.services.recommendations.ml.privacy.data_sanitizer import (
    MetadataSanitizer,
)

from app.services.recommendations.ml.privacy.privacy_config import (
    PrivacyConfig,
)

from app.services.recommendations.ml.privacy.privacy_exceptions import (
    MetadataSanitizationError,
)


def test_sensitive_keys_are_redacted():

    sanitizer = MetadataSanitizer()

    result = sanitizer.sanitize(
        {
            "password": "secret123",
            "api_key": "abc123",
            "email": "student@example.com",
            "stage": "baseline",
        }
    )

    assert result["password"] == "[REDACTED]"

    assert result["api_key"] == "[REDACTED]"

    assert result["email"] == "[REDACTED]"

    assert result["stage"] == "baseline"


def test_email_addresses_are_redacted():

    sanitizer = MetadataSanitizer()

    result = sanitizer.sanitize(
        {
            "message": "Contact student@example.com"
        }
    )

    assert "student@example.com" not in result["message"]


def test_phone_numbers_are_redacted():

    sanitizer = MetadataSanitizer()

    result = sanitizer.sanitize(
        {
            "message": "Contact number 9876543210"
        }
    )

    assert "9876543210" not in result["message"]


def test_ip_addresses_are_redacted():

    sanitizer = MetadataSanitizer()

    result = sanitizer.sanitize(
        {
            "message": "Request came from 192.168.1.10"
        }
    )

    assert "192.168.1.10" not in result["message"]


def test_bearer_tokens_are_redacted():

    sanitizer = MetadataSanitizer()

    result = sanitizer.sanitize(
        {
            "authorization": "Bearer abc123"
        }
    )

    assert result["authorization"] == "[REDACTED]"


def test_nested_metadata_is_sanitized():

    sanitizer = MetadataSanitizer()

    result = sanitizer.sanitize(
        {
            "experiment": {
                "user": {
                    "email": "student@example.com"
                }
            }
        }
    )

    assert (
        result["experiment"]["user"]["email"]
        == "[REDACTED]"
    )


def test_long_metadata_is_truncated():

    sanitizer = MetadataSanitizer(
        PrivacyConfig(
            maximum_metadata_string_length=10
        )
    )

    result = sanitizer.sanitize(
        {
            "description": "A" * 100
        }
    )

    assert result["description"].endswith("...[TRUNCATED]")


def test_unsupported_objects_are_rejected():

    sanitizer = MetadataSanitizer()

    class Unsupported:
        pass

    try:

        sanitizer.sanitize(
            {
                "value": Unsupported()
            }
        )

    except MetadataSanitizationError:

        pass

    else:

        raise AssertionError(
            "Unsupported metadata should be rejected."
        )


def test_sanitization_can_be_disabled():

    sanitizer = MetadataSanitizer(
        PrivacyConfig(
            redact_pii_from_metadata=False
        )
    )

    result = sanitizer.sanitize(
        {
            "email": "student@example.com"
        }
    )

    assert result["email"] == "student@example.com"