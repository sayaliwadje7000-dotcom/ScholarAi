"""Phase 18.11: authorization matrix tests for role dependencies."""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.security.permissions import (
    require_admin,
    require_educator,
    require_roles,
    require_student,
    require_student_or_admin,
)


@pytest.mark.parametrize(
    ("dependency", "roles", "expected_status"),
    [
        (require_student, {"student"}, None),
        (require_student, {"admin"}, 403),
        (require_educator, {"educator"}, None),
        (require_educator, {"student"}, 403),
        (require_admin, {"admin"}, None),
        (require_admin, {"educator"}, 403),
        (require_student_or_admin, {"student"}, None),
        (require_student_or_admin, {"admin"}, None),
        (require_student_or_admin, {"educator"}, 403),
        (require_student_or_admin, set(), 403),
    ],
)
def test_role_dependency_authorization_matrix(monkeypatch, dependency, roles, expected_status):
    user = SimpleNamespace(id="user-123")
    db = object()
    monkeypatch.setattr(
        "app.security.permissions.role_service.get_user_roles",
        lambda db, user_id: roles,
    )

    if expected_status is not None:
        with pytest.raises(HTTPException) as exc:
            dependency(current_user=user, db=db)
        assert exc.value.status_code == expected_status
    else:
        assert dependency(current_user=user, db=db) is user


def test_role_dependency_rejects_unknown_configured_role():
    with pytest.raises(ValueError):
        require_roles("superuser")
