import pytest

from pydantic import ValidationError

from app.schemas.auth import (
    UserRegistrationRequest,
)


def test_valid_registration_request():

    request = UserRegistrationRequest(
        full_name="ScholarAI Student",
        email="student@example.com",
        password="SecurePassword123!",
    )

    assert request.full_name == "ScholarAI Student"

    assert request.email == "student@example.com"

    assert (
        request.password.get_secret_value()
        == "SecurePassword123!"
    )


def test_email_is_normalized():

    request = UserRegistrationRequest(
        full_name="ScholarAI Student",
        email="Student@Example.com",
        password="SecurePassword123!",
    )

    assert request.email == "student@example.com"


def test_password_minimum_length():

    with pytest.raises(ValidationError):

        UserRegistrationRequest(
            full_name="ScholarAI Student",
            email="student@example.com",
            password="short",
        )


def test_password_maximum_length():

    with pytest.raises(ValidationError):

        UserRegistrationRequest(
            full_name="ScholarAI Student",
            email="student@example.com",
            password="A" * 129,
        )


def test_invalid_email_rejected():

    with pytest.raises(ValidationError):

        UserRegistrationRequest(
            full_name="ScholarAI Student",
            email="invalid-email",
            password="SecurePassword123!",
        )


def test_empty_name_rejected():

    with pytest.raises(ValidationError):

        UserRegistrationRequest(
            full_name=" ",
            email="student@example.com",
            password="SecurePassword123!",
        )


def test_extra_fields_rejected():

    with pytest.raises(ValidationError):

        UserRegistrationRequest(
            full_name="ScholarAI Student",
            email="student@example.com",
            password="SecurePassword123!",
            is_admin=True,
        )