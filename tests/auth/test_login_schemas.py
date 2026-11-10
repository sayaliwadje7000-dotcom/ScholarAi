import pytest

from pydantic import ValidationError

from app.schemas.auth import (
    UserLoginRequest,
)


def test_valid_login_request():

    request = UserLoginRequest(
        email="student@example.com",
        password="SecurePassword123!",
    )

    assert request.email == "student@example.com"

    assert (
        request.password.get_secret_value()
        == "SecurePassword123!"
    )


def test_login_email_normalization():

    request = UserLoginRequest(
        email="Student@Example.com",
        password="SecurePassword123!",
    )

    assert request.email == "student@example.com"


def test_invalid_login_email_rejected():

    with pytest.raises(ValidationError):

        UserLoginRequest(
            email="invalid-email",
            password="SecurePassword123!",
        )


def test_missing_password_rejected():

    with pytest.raises(ValidationError):

        UserLoginRequest(
            email="student@example.com",
        )


def test_extra_login_fields_rejected():

    with pytest.raises(ValidationError):

        UserLoginRequest(
            email="student@example.com",
            password="SecurePassword123!",
            is_admin=True,
        )


def test_short_password_allowed_for_login_schema():

    # Login verifies existing credentials.
    # Registration password policy must not silently
    # prevent verification of legacy passwords.

    request = UserLoginRequest(
        email="student@example.com",
        password="Short123!",
    )

    assert (
        request.password.get_secret_value()
        == "Short123!"
    )