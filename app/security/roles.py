"""
ScholarAI RBAC role definitions.
"""

from enum import Enum


class UserRoleName(str, Enum):

    STUDENT = "student"

    EDUCATOR = "educator"

    ADMIN = "admin"


VALID_ROLES = {
    role.value for role in UserRoleName
}


def normalize_role(role: str) -> str:

    if not isinstance(role, str):
        raise ValueError("Role must be a string.")

    normalized = role.strip().lower()

    if normalized not in VALID_ROLES:
        raise ValueError(
            f"Invalid role. Allowed roles: {sorted(VALID_ROLES)}"
        )

    return normalized


ROLE_HIERARCHY = {
    UserRoleName.STUDENT.value: 1,
    UserRoleName.EDUCATOR.value: 2,
    UserRoleName.ADMIN.value: 3,
}


def has_role(
    user_roles: set[str],
    required_role: str,
) -> bool:

    return required_role in user_roles
