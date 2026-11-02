import uuid

from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base
from app.models.user import User
from app.models.document import Document


def test_document_inherits_base():
    assert issubclass(Document, Base)


def test_document_table_name():
    assert Document.__tablename__ == "documents"


def test_document_primary_key():
    column = Document.__table__.columns["id"]

    assert column.primary_key
    assert isinstance(column.type, UUID)


def test_document_uuid_generation():
    generator = Document.__table__.columns["id"].default.arg

    generated_id = generator(None)

    assert isinstance(generated_id, uuid.UUID)


def test_document_user_foreign_key():
    column = Document.__table__.columns["user_id"]

    assert column.nullable is False

    foreign_key = next(iter(column.foreign_keys))

    assert foreign_key.target_fullname == "users.id"
    assert foreign_key.ondelete == "CASCADE"


def test_document_filename_column():
    column = Document.__table__.columns["original_filename"]

    assert column.type.length == 255
    assert column.nullable is False


def test_document_storage_key_column():
    column = Document.__table__.columns["storage_key"]

    assert column.type.length == 512
    assert column.nullable is False


def test_document_storage_key_unique():
    constraints = {
        constraint.name
        for constraint in Document.__table__.constraints
    }

    assert "uq_documents_storage_key" in constraints


def test_document_mime_type_column():
    column = Document.__table__.columns["mime_type"]

    assert column.type.length == 100
    assert column.nullable is False


def test_document_file_size_column():
    column = Document.__table__.columns["file_size_bytes"]

    assert str(column.type) == "BIGINT"
    assert column.nullable is False


def test_document_checksum_column():
    column = Document.__table__.columns["checksum_sha256"]

    assert column.type.length == 64
    assert column.nullable is False


def test_document_page_count_column():
    column = Document.__table__.columns["page_count"]

    assert str(column.type) == "INTEGER"
    assert column.nullable is True


def test_document_processing_status_column():
    column = Document.__table__.columns["processing_status"]

    assert column.type.length == 20
    assert column.nullable is False


def test_document_timestamp_column():
    column = Document.__table__.columns["uploaded_at"]

    assert column.type.timezone is True
    assert column.nullable is False


def test_document_user_relationship():
    assert "user" in Document.__mapper__.relationships


def test_user_documents_relationship():
    assert "documents" in User.__mapper__.relationships

    relationship = User.__mapper__.relationships["documents"]

    assert relationship.uselist is True


def test_document_constraints():
    constraints = {
        constraint.name
        for constraint in Document.__table__.constraints
    }

    assert "ck_documents_positive_file_size" in constraints
    assert "ck_documents_positive_page_count" in constraints
    assert "ck_documents_valid_processing_status" in constraints
    assert "ck_documents_valid_sha256" in constraints


def test_document_indexes():
    indexes = {
        index.name
        for index in Document.__table__.indexes
    }

    assert "ix_documents_user_id" in indexes
    assert "ix_documents_processing_status" in indexes
    assert "ix_documents_user_uploaded" in indexes


def test_document_instance_creation():
    document = Document(
        user_id=uuid.uuid4(),
        original_filename="data_structures.pdf",
        storage_key="users/test/documents/example.pdf",
        mime_type="application/pdf",
        file_size_bytes=102400,
        checksum_sha256="a" * 64,
        page_count=25,
        processing_status="pending",
    )

    assert document.original_filename == "data_structures.pdf"
    assert document.storage_key == "users/test/documents/example.pdf"
    assert document.mime_type == "application/pdf"
    assert document.file_size_bytes == 102400
    assert document.checksum_sha256 == "a" * 64
    assert document.page_count == 25
    assert document.processing_status == "pending"


def test_document_repr():
    document = Document(
        user_id=uuid.uuid4(),
        original_filename="machine_learning.pdf",
        storage_key="users/test/documents/ml.pdf",
        mime_type="application/pdf",
        file_size_bytes=204800,
        checksum_sha256="b" * 64,
    )

    assert "machine_learning.pdf" in repr(document)