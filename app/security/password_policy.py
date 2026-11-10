"""
ScholarAI password policy enforcement.
"""

import unicodedata

from app.core.password_config import (
    password_security_settings,
)


def validate_password(password: str) -> None:
    """
    Validate a password against ScholarAI security policy.

    Raises:
        TypeError: If the password is not a string.
        ValueError: If the password violates the policy.
    """

    if not isinstance(password, str):

        raise TypeError(
            "Password must be a string."
        )

    settings = password_security_settings

    if not password:

        raise ValueError(
            "Password cannot be empty."
        )

    if len(password) < settings.minimum_password_length:

        raise ValueError(
            f"Password must contain at least "
            f"{settings.minimum_password_length} characters."
        )

    if len(password) > settings.maximum_password_length:

        raise ValueError(
            f"Password cannot exceed "
            f"{settings.maximum_password_length} characters."
        )

    if len(password.encode("utf-8")) > settings.maximum_password_bytes:

        raise ValueError(
            "Password exceeds the maximum supported byte length."
        )

    if password.isspace():

        raise ValueError(
            "Password cannot contain only whitespace."
        )

    if any(
        unicodedata.category(character) == "Cc"
        for character in password
    ):

        raise ValueError(
            "Password cannot contain control characters."
        )