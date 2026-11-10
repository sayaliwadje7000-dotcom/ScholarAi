from pydantic import ValidationError

import pytest

from app.schemas.auth import (
    UserRegistrationRequest,
)


def test_registration_accepts_valid_password():

    request = UserRegistrationRequest(
        full_name="ScholarAI Student",
        email="student@example.com",
        password="SecurePassword123!",
    )

    assert (
        request.password.get_secret_value()
        == "SecurePassword123!"
    )


def test_registration_rejects_short_password():

    with pytest.raises(ValidationError):

        UserRegistrationRequest(
            full_name="ScholarAI Student",
            email="student@example.com",
            password="Short123!",
        )


def test_registration_rejects_whitespace_password():

    with pytest.raises(ValidationError):

        UserRegistrationRequest(
            full_name="ScholarAI Student",
            email="student@example.com",
            password=" " * 20,
        )


def test_registration_rejects_control_characters():

    with pytest.raises(ValidationError):

        UserRegistrationRequest(
            full_name="ScholarAI Student",
            email="student@example.com",
            password="SecurePassword123!\n",
        )


def test_registration_accepts_passphrase():

    request = UserRegistrationRequest(
        full_name="ScholarAI Student",
        email="student@example.com",
        password="My Secure Study Passphrase",
    )

    assert request.password is not None