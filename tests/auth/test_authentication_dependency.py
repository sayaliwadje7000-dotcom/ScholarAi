from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.user_session import UserSession
from app.security.token import create_access_token


def credentials(token: str):
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def session_bound_token(user_id, session_id):
    token, _ = create_access_token(user_id=user_id, session_id=session_id)
    return credentials(token)


def test_rejects_missing_credentials():
    db = MagicMock()
    with pytest.raises(HTTPException) as exc:
        get_current_user(credentials=None, db=db)
    assert exc.value.status_code == 401
    db.scalar.assert_not_called()


def test_rejects_invalid_token():
    db = MagicMock()
    with pytest.raises(HTTPException) as exc:
        get_current_user(credentials=credentials("invalid.token.value"), db=db)
    assert exc.value.status_code == 401
    db.scalar.assert_not_called()


def test_rejects_access_token_without_session_id():
    user_id = uuid4()
    token, _ = create_access_token(user_id=user_id)
    db = MagicMock()
    with pytest.raises(HTTPException) as exc:
        get_current_user(credentials=credentials(token), db=db)
    assert exc.value.status_code == 401
    db.scalar.assert_not_called()


def test_returns_active_user_with_active_session():
    user_id, session_id = uuid4(), uuid4()
    user = MagicMock(spec=User)
    user.id = user_id
    user.is_active = True
    active_session = MagicMock(spec=UserSession)
    active_session.id = session_id
    active_session.user_id = user_id
    active_session.revoked_at = None
    active_session.expires_at = datetime.now(timezone.utc) + timedelta(days=1)
    db = MagicMock()
    db.scalar.side_effect = [user, active_session]

    result = get_current_user(
        credentials=session_bound_token(user_id, session_id), db=db
    )

    assert result is user
    assert db.scalar.call_count == 2


@pytest.mark.parametrize("session_result", [None])
def test_rejects_revoked_or_missing_session(session_result):
    user_id, session_id = uuid4(), uuid4()
    user = MagicMock(spec=User)
    user.id = user_id
    user.is_active = True
    db = MagicMock()
    db.scalar.side_effect = [user, session_result]

    with pytest.raises(HTTPException) as exc:
        get_current_user(
            credentials=session_bound_token(user_id, session_id), db=db
        )
    assert exc.value.status_code == 401


def test_rejects_inactive_user_without_session_lookup():
    user_id, session_id = uuid4(), uuid4()
    user = MagicMock(spec=User)
    user.id = user_id
    user.is_active = False
    db = MagicMock()
    db.scalar.return_value = user

    with pytest.raises(HTTPException) as exc:
        get_current_user(
            credentials=session_bound_token(user_id, session_id), db=db
        )
    assert exc.value.status_code == 401
    db.scalar.assert_called_once()


def test_database_failure_returns_503():
    user_id, session_id = uuid4(), uuid4()
    db = MagicMock()
    db.scalar.side_effect = RuntimeError("database unavailable")

    with pytest.raises(HTTPException) as exc:
        get_current_user(
            credentials=session_bound_token(user_id, session_id), db=db
        )
    assert exc.value.status_code == 503
