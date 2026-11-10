from unittest.mock import MagicMock

from uuid import uuid4

import pytest

from fastapi import HTTPException

from fastapi.security import (
    HTTPAuthorizationCredentials,
)

from app.api.dependencies import get_current_user

from app.security.token import create_access_token

from app.models.user import User


def create_credentials(token: str):

    return HTTPAuthorizationCredentials(

        scheme="Bearer",

        credentials=token,

    )


def test_get_current_user_rejects_missing_credentials():

    db = MagicMock()

    with pytest.raises(HTTPException) as exc:

        get_current_user(
            credentials=None,
            db=db,
        )

    assert exc.value.status_code == 401

    db.scalar.assert_not_called()


def test_get_current_user_rejects_invalid_token():

    db = MagicMock()

    credentials = create_credentials(
        "invalid.token.value"
    )

    with pytest.raises(HTTPException) as exc:

        get_current_user(
            credentials=credentials,
            db=db,
        )

    assert exc.value.status_code == 401

    db.scalar.assert_not_called()


def test_get_current_user_returns_active_user():

    user_id = uuid4()

    user = MagicMock(spec=User)

    user.id = user_id

    user.is_active = True

    token, _ = create_access_token(
        user_id=user_id,
    )

    db = MagicMock()

    db.scalar.return_value = user

    result = get_current_user(

        credentials=create_credentials(token),

        db=db,

    )

    assert result is user

    db.scalar.assert_called_once()


def test_get_current_user_rejects_inactive_user():

    user_id = uuid4()

    user = MagicMock(spec=User)

    user.id = user_id

    user.is_active = False

    token, _ = create_access_token(
        user_id=user_id,
    )

    db = MagicMock()

    db.scalar.return_value = user

    with pytest.raises(HTTPException) as exc:

        get_current_user(

            credentials=create_credentials(token),

            db=db,

        )

    assert exc.value.status_code == 401


def test_get_current_user_rejects_deleted_user():

    token, _ = create_access_token(
        user_id=uuid4(),
    )

    db = MagicMock()

    db.scalar.return_value = None

    with pytest.raises(HTTPException) as exc:

        get_current_user(

            credentials=create_credentials(token),

            db=db,

        )

    assert exc.value.status_code == 401


def test_get_current_user_returns_503_on_database_failure():

    token, _ = create_access_token(
        user_id=uuid4(),
    )

    db = MagicMock()

    db.scalar.side_effect = RuntimeError(
        "Database unavailable"
    )

    with pytest.raises(HTTPException) as exc:

        get_current_user(

            credentials=create_credentials(token),

            db=db,

        )

    assert exc.value.status_code == 503