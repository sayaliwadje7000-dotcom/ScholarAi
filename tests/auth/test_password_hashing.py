import pytest

from app.security.password import (
    hash_password,
    verify_password,
    password_hash_needs_rehash,
    verify_password_and_update,
)


def test_password_is_hashed():

    password = "SecurePassword123!"

    password_hash = hash_password(password)

    assert password_hash != password

    assert password_hash.startswith("$argon2id$")


def test_correct_password_verifies():

    password = "SecurePassword123!"

    password_hash = hash_password(password)

    assert verify_password(
        password,
        password_hash,
    ) is True


def test_incorrect_password_fails():

    password_hash = hash_password(
        "SecurePassword123!"
    )

    assert verify_password(
        "WrongPassword123!",
        password_hash,
    ) is False


def test_different_hashes_for_same_password():

    password = "SecurePassword123!"

    first_hash = hash_password(password)

    second_hash = hash_password(password)

    assert first_hash != second_hash

    assert verify_password(
        password,
        first_hash,
    )

    assert verify_password(
        password,
        second_hash,
    )


def test_empty_password_rejected():

    with pytest.raises(ValueError):

        hash_password("")


def test_invalid_hash_returns_false():

    assert verify_password(
        "SecurePassword123!",
        "invalid-hash",
    ) is False


def test_non_string_password_returns_false():

    assert verify_password(
        123456,
        "$argon2id$invalid",
    ) is False


def test_non_string_hash_returns_false():

    assert verify_password(
        "SecurePassword123!",
        None,
    ) is False


def test_current_hash_does_not_need_rehash():

    password_hash = hash_password(
        "SecurePassword123!"
    )

    assert password_hash_needs_rehash(
        password_hash
    ) is False


def test_invalid_hash_needs_rehash():

    assert password_hash_needs_rehash(
        "invalid-hash"
    ) is True


def test_verification_and_update_success():

    password = "SecurePassword123!"

    password_hash = hash_password(password)

    verified, updated_hash = verify_password_and_update(
        password,
        password_hash,
    )

    assert verified is True

    assert updated_hash is None


def test_verification_and_update_failure():

    password_hash = hash_password(
        "SecurePassword123!"
    )

    verified, updated_hash = verify_password_and_update(
        "IncorrectPassword123!",
        password_hash,
    )

    assert verified is False

    assert updated_hash is None