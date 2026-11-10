import pytest

from app.security.roles import (
    UserRoleName,
    normalize_role,
    has_role,
    VALID_ROLES,
)


def test_valid_roles_exist():

    assert VALID_ROLES == {
        "student",
        "educator",
        "admin",
    }


@pytest.mark.parametrize(
    "role",
    [
        "student",
        "educator",
        "admin",
    ],
)
def test_normalize_valid_role(role):

    assert normalize_role(role) == role


def test_normalize_role_is_case_insensitive():

    assert normalize_role("ADMIN") == "admin"


def test_normalize_role_removes_outer_whitespace():

    assert normalize_role(" student ") == "student"


@pytest.mark.parametrize(
    "role",
    [
        "",
        "superuser",
        "root",
        "moderator",
        "unknown",
    ],
)
def test_invalid_roles_are_rejected(role):

    with pytest.raises(ValueError):
        normalize_role(role)


def test_non_string_role_is_rejected():

    with pytest.raises(ValueError):
        normalize_role(None)


def test_has_role():

    roles = {"student", "educator"}

    assert has_role(roles, "student")
    assert has_role(roles, "educator")
    assert not has_role(roles, "admin")


def test_role_enum_values():

    assert UserRoleName.STUDENT.value == "student"
    assert UserRoleName.EDUCATOR.value == "educator"
    assert UserRoleName.ADMIN.value == "admin"
