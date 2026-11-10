import pytest

from app.security.password_policy import (
    validate_password,
)


def test_valid_password():

    validate_password(
        "SecurePassword123!"
    )


def test_password_below_minimum_length():

    with pytest.raises(ValueError):

        validate_password(
            "Short123!"
        )


def test_password_above_maximum_length():

    with pytest.raises(ValueError):

        validate_password(
            "A" * 129
        )


def test_empty_password_rejected():

    with pytest.raises(ValueError):

        validate_password("")


def test_whitespace_only_password_rejected():

    with pytest.raises(ValueError):

        validate_password(" " * 20)


def test_internal_spaces_are_allowed():

    validate_password(
        "My Secure Study Passphrase"
    )


def test_unicode_password_supported():

    validate_password(
        "ScholarAI安全密码123!"
    )


def test_control_characters_rejected():

    with pytest.raises(ValueError):

        validate_password(
            "SecurePassword123!\n"
        )


def test_non_string_password_rejected():

    with pytest.raises(TypeError):

        validate_password(123456789012)


def test_maximum_byte_length_enforced():

    with pytest.raises(ValueError):

        validate_password(
            "€" * 128
        )