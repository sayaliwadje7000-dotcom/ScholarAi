from unittest.mock import MagicMock

import pytest

from app.models.user import User

from app.schemas.auth import (
    UserRegistrationRequest,
)

from app.services.auth_service import AuthService


def create_registration_request():

    return UserRegistrationRequest(
        full_name="ScholarAI Student",
        email="student@example.com",
        password="SecurePassword123!",
    )


def test_register_user_success(monkeypatch):

    service = AuthService()

    db = MagicMock()

    db.scalar.return_value = None

    db.refresh.side_effect = (
        lambda user: setattr(
            user,
            "id",
            __import__("uuid").uuid4(),
        )
    )

    user = service.register_user(
        db=db,
        request=create_registration_request(),
    )

    assert isinstance(user, User)

    assert user.email == "student@example.com"

    assert user.full_name == "ScholarAI Student"

    assert user.password_hash is not None

    assert user.password_hash != "SecurePassword123!"

    db.add.assert_called_once_with(user)

    db.commit.assert_called_once()

    db.refresh.assert_called_once_with(user)


def test_duplicate_email_rejected():

    service = AuthService()

    db = MagicMock()

    db.scalar.return_value = User(
        full_name="Existing Student",
        email="student@example.com",
    )

    with pytest.raises(
        ValueError,
        match="already exists",
    ):

        service.register_user(
            db=db,
            request=create_registration_request(),
        )

    db.add.assert_not_called()

    db.commit.assert_not_called()


def test_database_integrity_conflict(monkeypatch):

    from sqlalchemy.exc import IntegrityError

    service = AuthService()

    db = MagicMock()

    db.scalar.return_value = None

    db.commit.side_effect = IntegrityError(
        "INSERT",
        {},
        Exception("Unique constraint violation"),
    )

    with pytest.raises(
        ValueError,
        match="already exists",
    ):

        service.register_user(
            db=db,
            request=create_registration_request(),
        )

    db.rollback.assert_called_once()


def test_registration_rolls_back_on_unexpected_error():

    service = AuthService()

    db = MagicMock()

    db.scalar.return_value = None

    db.commit.side_effect = RuntimeError(
        "Database unavailable"
    )

    with pytest.raises(RuntimeError):

        service.register_user(
            db=db,
            request=create_registration_request(),
        )

    db.rollback.assert_called_once()