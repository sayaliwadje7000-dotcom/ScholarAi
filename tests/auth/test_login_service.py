import uuid

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.models.user import User

from app.schemas.auth import (
    UserLoginRequest,
)

from app.services.auth_service import (
    AuthService,
)

from app.services.auth_exceptions import (
    AuthenticationError,
)

from app.security.password import (
    hash_password,
)


def create_login_request(
    email="student@example.com",
    password="SecurePassword123!",
):

    return UserLoginRequest(
        email=email,
        password=password,
    )


def create_user(
    password="SecurePassword123!",
    is_active=True,
):

    return User(
        id=uuid.uuid4(),
        full_name="ScholarAI Student",
        email="student@example.com",
        password_hash=hash_password(password),
        is_active=is_active,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def test_authenticate_user_success():

    service = AuthService()

    db = MagicMock()

    user = create_user()

    db.scalar.return_value = user

    result = service.authenticate_user(
        db=db,
        request=create_login_request(),
    )

    assert result is user

    db.commit.assert_not_called()


def test_authenticate_user_unknown_email():

    service = AuthService()

    db = MagicMock()

    db.scalar.return_value = None

    with pytest.raises(AuthenticationError):

        service.authenticate_user(
            db=db,
            request=create_login_request(),
        )

    db.commit.assert_not_called()


def test_authenticate_user_incorrect_password():

    service = AuthService()

    db = MagicMock()

    user = create_user()

    db.scalar.return_value = user

    with pytest.raises(AuthenticationError):

        service.authenticate_user(
            db=db,
            request=create_login_request(
                password="WrongPassword123!",
            ),
        )

    db.commit.assert_not_called()


def test_authenticate_user_inactive_account():

    service = AuthService()

    db = MagicMock()

    user = create_user(
        is_active=False,
    )

    db.scalar.return_value = user

    with pytest.raises(AuthenticationError):

        service.authenticate_user(
            db=db,
            request=create_login_request(),
        )

    db.commit.assert_not_called()


def test_authenticate_user_without_password_hash():

    service = AuthService()

    db = MagicMock()

    user = User(
        id=uuid.uuid4(),
        full_name="Legacy Student",
        email="student@example.com",
        password_hash=None,
        is_active=True,
    )

    db.scalar.return_value = user

    with pytest.raises(AuthenticationError):

        service.authenticate_user(
            db=db,
            request=create_login_request(),
        )

    db.commit.assert_not_called()


def test_authenticate_user_upgrades_old_hash(monkeypatch):

    service = AuthService()

    db = MagicMock()

    user = create_user()

    db.scalar.return_value = user

    new_hash = hash_password(
        "SecurePassword123!"
    )

    from app.services import auth_service

    monkeypatch.setattr(
        auth_service,
        "verify_password_and_update",
        lambda password, password_hash: (
            True,
            new_hash,
        ),
    )

    result = service.authenticate_user(
        db=db,
        request=create_login_request(),
    )

    assert result is user

    assert user.password_hash == new_hash

    db.commit.assert_called_once()

    db.refresh.assert_called_once_with(user)


def test_hash_upgrade_failure_rolls_back(monkeypatch):

    service = AuthService()

    db = MagicMock()

    user = create_user()

    original_hash = user.password_hash

    db.scalar.return_value = user

    new_hash = hash_password(
        "SecurePassword123!"
    )

    from app.services import auth_service

    monkeypatch.setattr(
        auth_service,
        "verify_password_and_update",
        lambda password, password_hash: (
            True,
            new_hash,
        ),
    )

    db.commit.side_effect = RuntimeError(
        "Database unavailable"
    )

    # Simulate the ORM restoring the object's
    # persisted state when the transaction rolls back.
    def simulate_rollback():

        user.password_hash = original_hash

    db.rollback.side_effect = simulate_rollback

    with pytest.raises(RuntimeError):

        service.authenticate_user(
            db=db,
            request=create_login_request(),
        )

    db.rollback.assert_called_once()

    assert user.password_hash == original_hash