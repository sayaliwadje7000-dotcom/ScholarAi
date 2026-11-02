from pathlib import Path

import pytest

from app.core.document_config import (
    DocumentSettings,
    get_positive_integer,
    get_boolean,
    get_storage_directories,
    initialize_document_storage,
)


# ============================================================
# INTEGER CONFIGURATION TESTS
# ============================================================

def test_positive_integer_configuration(monkeypatch):

    monkeypatch.setenv(
        "TEST_DOCUMENT_LIMIT",
        "100",
    )

    result = get_positive_integer(
        "TEST_DOCUMENT_LIMIT",
        50,
    )

    assert result == 100


def test_invalid_integer_configuration(monkeypatch):

    monkeypatch.setenv(
        "TEST_DOCUMENT_LIMIT",
        "invalid",
    )

    with pytest.raises(ValueError):

        get_positive_integer(
            "TEST_DOCUMENT_LIMIT",
            50,
        )


def test_zero_integer_configuration(monkeypatch):

    monkeypatch.setenv(
        "TEST_DOCUMENT_LIMIT",
        "0",
    )

    with pytest.raises(ValueError):

        get_positive_integer(
            "TEST_DOCUMENT_LIMIT",
            50,
        )


# ============================================================
# BOOLEAN CONFIGURATION TESTS
# ============================================================

def test_boolean_true(monkeypatch):

    monkeypatch.setenv(
        "TEST_DOCUMENT_BOOLEAN",
        "true",
    )

    assert get_boolean(
        "TEST_DOCUMENT_BOOLEAN",
        False,
    ) is True


def test_boolean_false(monkeypatch):

    monkeypatch.setenv(
        "TEST_DOCUMENT_BOOLEAN",
        "false",
    )

    assert get_boolean(
        "TEST_DOCUMENT_BOOLEAN",
        True,
    ) is False


def test_invalid_boolean(monkeypatch):

    monkeypatch.setenv(
        "TEST_DOCUMENT_BOOLEAN",
        "unknown",
    )

    with pytest.raises(ValueError):

        get_boolean(
            "TEST_DOCUMENT_BOOLEAN",
            False,
        )


# ============================================================
# STORAGE PATH TESTS
# ============================================================

def test_storage_directory_structure(tmp_path):

    settings = DocumentSettings(
        storage_root=tmp_path / "storage",

        max_file_size_bytes=20 * 1024 * 1024,

        max_pages=100,

        allowed_extensions=(".pdf",),

        allowed_mime_types=("application/pdf",),

        create_storage_directories=True,
    )

    directories = get_storage_directories(
        settings
    )

    assert directories["documents"] == (
        tmp_path / "storage" / "documents"
    )

    assert directories["processed"] == (
        tmp_path / "storage" / "processed"
    )

    assert directories["temporary"] == (
        tmp_path / "storage" / "temporary"
    )


def test_storage_initialization(tmp_path):

    settings = DocumentSettings(
        storage_root=tmp_path / "storage",

        max_file_size_bytes=20 * 1024 * 1024,

        max_pages=100,

        allowed_extensions=(".pdf",),

        allowed_mime_types=("application/pdf",),

        create_storage_directories=True,
    )

    directories = initialize_document_storage(
        settings
    )

    assert directories["documents"].is_dir()

    assert directories["processed"].is_dir()

    assert directories["temporary"].is_dir()


def test_storage_initialization_is_idempotent(tmp_path):

    settings = DocumentSettings(
        storage_root=tmp_path / "storage",

        max_file_size_bytes=20 * 1024 * 1024,

        max_pages=100,

        allowed_extensions=(".pdf",),

        allowed_mime_types=("application/pdf",),

        create_storage_directories=True,
    )

    first = initialize_document_storage(
        settings
    )

    second = initialize_document_storage(
        settings
    )

    assert first == second


def test_storage_creation_can_be_disabled(tmp_path):

    settings = DocumentSettings(
        storage_root=tmp_path / "storage",

        max_file_size_bytes=20 * 1024 * 1024,

        max_pages=100,

        allowed_extensions=(".pdf",),

        allowed_mime_types=("application/pdf",),

        create_storage_directories=False,
    )

    directories = initialize_document_storage(
        settings
    )

    assert not directories["documents"].exists()