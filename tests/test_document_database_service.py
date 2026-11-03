import uuid

from unittest.mock import MagicMock, patch

import pytest

from sqlalchemy.exc import SQLAlchemyError

from app.models.document import Document

from app.services.document_storage_service import StoredDocument

from app.services.document_database_service import (
    DocumentNotFoundError,
    DocumentPersistenceError,
    DocumentConsistencyError,
    create_document_record,
    store_and_register_document,
    get_document_by_id,
    get_user_document,
    list_user_documents,
    count_user_documents,
)


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def db():
    return MagicMock()


@pytest.fixture
def user_id():
    return uuid.uuid4()


@pytest.fixture
def stored_document():
    return StoredDocument(
        document_id=uuid.uuid4(),
        storage_key="documents/test-document.pdf",
        original_filename="test-document.pdf",
        mime_type="application/pdf",
        file_size_bytes=2048,
        checksum_sha256="a" * 64,
        page_count=5,
    )


# ============================================================
# DOCUMENT CREATION
# ============================================================

def test_create_document_record_success(
    db,
    user_id,
    stored_document,
):
    result = create_document_record(
        db=db,
        user_id=user_id,
        stored_document=stored_document,
    )

    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()

    assert isinstance(result, Document)
    assert result.id == stored_document.document_id
    assert result.user_id == user_id
    assert result.original_filename == "test-document.pdf"
    assert result.storage_key == stored_document.storage_key
    assert result.processing_status == "pending"


def test_create_document_record_rejects_invalid_user(
    db,
    stored_document,
):
    with pytest.raises(ValueError):
        create_document_record(
            db=db,
            user_id="invalid-user",
            stored_document=stored_document,
        )

    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_create_document_record_rejects_invalid_document(
    db,
    user_id,
):
    with pytest.raises(ValueError):
        create_document_record(
            db=db,
            user_id=user_id,
            stored_document=None,
        )

    db.add.assert_not_called()


def test_create_document_record_rolls_back_on_failure(
    db,
    user_id,
    stored_document,
):
    db.commit.side_effect = SQLAlchemyError(
        "Database failure"
    )

    with pytest.raises(DocumentPersistenceError):
        create_document_record(
            db=db,
            user_id=user_id,
            stored_document=stored_document,
        )

    db.rollback.assert_called_once()


# ============================================================
# STORAGE + DATABASE CONSISTENCY
# ============================================================

@patch(
    "app.services.document_database_service.save_document"
)
def test_store_and_register_document_success(
    mock_save,
    db,
    user_id,
    stored_document,
):
    mock_save.return_value = stored_document

    result = store_and_register_document(
        db=db,
        user_id=user_id,
        content=b"fake-pdf-content",
        original_filename="test.pdf",
        content_type="application/pdf",
    )

    assert result.id == stored_document.document_id

    mock_save.assert_called_once()
    db.add.assert_called_once()
    db.commit.assert_called_once()


@patch(
    "app.services.document_database_service.delete_document"
)
@patch(
    "app.services.document_database_service.save_document"
)
def test_storage_cleanup_when_database_persistence_fails(
    mock_save,
    mock_delete,
    db,
    user_id,
    stored_document,
):
    mock_save.return_value = stored_document

    db.commit.side_effect = SQLAlchemyError(
        "Database unavailable"
    )

    with pytest.raises(DocumentPersistenceError):
        store_and_register_document(
            db=db,
            user_id=user_id,
            content=b"fake-pdf-content",
            original_filename="test.pdf",
            content_type="application/pdf",
        )

    mock_delete.assert_called_once_with(
        stored_document.storage_key,
    )


@patch(
    "app.services.document_database_service.delete_document"
)
@patch(
    "app.services.document_database_service.save_document"
)
def test_consistency_error_when_cleanup_fails(
    mock_save,
    mock_delete,
    db,
    user_id,
    stored_document,
):
    mock_save.return_value = stored_document

    db.commit.side_effect = SQLAlchemyError(
        "Database unavailable"
    )

    mock_delete.side_effect = OSError(
        "Storage unavailable"
    )

    with pytest.raises(DocumentConsistencyError):
        store_and_register_document(
            db=db,
            user_id=user_id,
            content=b"fake-pdf-content",
            original_filename="test.pdf",
            content_type="application/pdf",
        )


# ============================================================
# DOCUMENT RETRIEVAL
# ============================================================

def test_get_document_by_id_success(db):
    expected = MagicMock(spec=Document)
    db.scalar.return_value = expected

    result = get_document_by_id(
        db=db,
        document_id=uuid.uuid4(),
    )

    assert result is expected
    db.scalar.assert_called_once()


def test_get_document_by_id_not_found(db):
    db.scalar.return_value = None

    with pytest.raises(DocumentNotFoundError):
        get_document_by_id(
            db=db,
            document_id=uuid.uuid4(),
        )


# ============================================================
# OWNER VALIDATION
# ============================================================

def test_get_user_document_success(db):
    expected = MagicMock(spec=Document)
    db.scalar.return_value = expected

    result = get_user_document(
        db=db,
        document_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
    )

    assert result is expected
    db.scalar.assert_called_once()


def test_get_user_document_rejects_other_owner(db):
    db.scalar.return_value = None

    with pytest.raises(DocumentNotFoundError):
        get_user_document(
            db=db,
            document_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )


# ============================================================
# DOCUMENT LISTING
# ============================================================

def test_list_user_documents_success(db, user_id):
    expected = [
        MagicMock(spec=Document),
        MagicMock(spec=Document),
    ]

    db.scalars.return_value.all.return_value = expected

    result = list_user_documents(
        db=db,
        user_id=user_id,
        offset=0,
        limit=20,
    )

    assert result == expected
    db.scalars.assert_called_once()


def test_list_user_documents_rejects_negative_offset(
    db,
    user_id,
):
    with pytest.raises(ValueError):
        list_user_documents(
            db=db,
            user_id=user_id,
            offset=-1,
        )


def test_list_user_documents_rejects_zero_limit(
    db,
    user_id,
):
    with pytest.raises(ValueError):
        list_user_documents(
            db=db,
            user_id=user_id,
            limit=0,
        )


def test_list_user_documents_rejects_excessive_limit(
    db,
    user_id,
):
    with pytest.raises(ValueError):
        list_user_documents(
            db=db,
            user_id=user_id,
            limit=101,
        )


# ============================================================
# DOCUMENT COUNT
# ============================================================

def test_count_user_documents(db, user_id):
    db.scalar.return_value = 12

    result = count_user_documents(
        db=db,
        user_id=user_id,
    )

    assert result == 12


def test_count_user_documents_returns_zero(db, user_id):
    db.scalar.return_value = None

    result = count_user_documents(
        db=db,
        user_id=user_id,
    )

    assert result == 0