import pytest

from app.services.role_service import role_service


@pytest.fixture(autouse=True)
def default_student_role_for_legacy_api_tests(request, monkeypatch):
    """
    Legacy API tests that override authentication represent
    ordinary student users. Give those users a student role.

    Dedicated authentication and authorization tests retain
    their own role behavior.
    """
    path = str(request.node.path).replace("\\", "/")

    if "/tests/auth/" in path or "/tests/services/" in path:
        return

    monkeypatch.setattr(
        role_service,
        "get_user_roles",
        lambda db, user_id: {"student"},
    )