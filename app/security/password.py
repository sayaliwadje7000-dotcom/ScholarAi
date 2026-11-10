"""
ScholarAI Argon2id password hashing service.

Responsibilities:
- Secure password hashing.
- Password verification.
- Malformed hash handling.
- Hash parameter upgrade detection.
- Safe password verification with rehash support.
"""

from argon2 import PasswordHasher
from argon2.low_level import Type

from argon2.exceptions import (
    HashingError,
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)

from app.core.password_config import (
    password_security_settings,
)

from app.security.password_policy import (
    validate_password,
)


_settings = password_security_settings


_password_hasher = PasswordHasher(
    time_cost=_settings.time_cost,
    memory_cost=_settings.memory_cost,
    parallelism=_settings.parallelism,
    hash_len=_settings.hash_len,
    salt_len=_settings.salt_len,
    type=Type.ID,
)


def hash_password(password: str) -> str:
    """
    Generate a secure Argon2id password hash.

    The original password is never stored.
    """

    validate_password(password)

    try:

        password_hash = _password_hasher.hash(
            password
        )

        if not password_hash.startswith("$argon2id$"):

            raise RuntimeError(
                "Unexpected password hashing algorithm."
            )

        return password_hash

    except HashingError as exc:

        raise RuntimeError(
            "Password hashing failed."
        ) from exc


def verify_password(
    password: str,
    password_hash: str,
) -> bool:
    """
    Verify a password against a stored Argon2id hash.

    Returns False for:
    - Incorrect passwords.
    - Empty inputs.
    - Malformed hashes.
    - Unsupported hash formats.
    """

    if not isinstance(password, str):
        return False

    if not isinstance(password_hash, str):
        return False

    if not password or not password_hash:
        return False

    if not password_hash.startswith("$argon2id$"):
        return False

    try:

        return _password_hasher.verify(
            password_hash,
            password,
        )

    except (
        VerifyMismatchError,
        VerificationError,
        InvalidHashError,
    ):

        return False


def password_hash_needs_rehash(
    password_hash: str,
) -> bool:
    """
    Determine whether an existing password hash
    needs upgrading to current Argon2id parameters.
    """

    if not isinstance(password_hash, str):
        return True

    if not password_hash.startswith("$argon2id$"):
        return True

    try:

        return _password_hasher.check_needs_rehash(
            password_hash
        )

    except (
        VerificationError,
        InvalidHashError,
        ValueError,
    ):

        return True


def verify_password_and_update(
    password: str,
    password_hash: str,
) -> tuple[bool, str | None]:
    """
    Verify a password and generate an upgraded hash
    when the stored hash uses outdated parameters.

    Returns:
        (False, None): Verification failed.
        (True, None): Verification succeeded; no upgrade needed.
        (True, new_hash): Verification succeeded; upgrade required.
    """

    if not verify_password(
        password,
        password_hash,
    ):

        return False, None

    if not password_hash_needs_rehash(
        password_hash
    ):

        return True, None

    try:

        upgraded_hash = hash_password(password)

        return True, upgraded_hash

    except (ValueError, RuntimeError):

        # Authentication must not silently accept an
        # invalid password or return an invalid replacement.
        raise RuntimeError(
            "Password hash upgrade failed."
        )