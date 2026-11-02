import uuid

import pytest

from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from app.database.session import SessionLocal

from app.models.user import User
from app.models.document import Document


def test_document_database_persistence():

    email = f"phase67_{uuid.uuid4().hex}@example.com"

    db = SessionLocal()

    user_id = None
    document_id = None

    try:

        # Create user.

        user = User(
            full_name="Document Test User",
            email=email,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        user_id = user.id

        # Create document.

        document = Document(
            user_id=user_id,
            original_filename="data_structures.pdf",
            storage_key=f"users/{user_id}/documents/{uuid.uuid4().hex}.pdf",
            mime_type="application/pdf",
            file_size_bytes=102400,
            checksum_sha256="a" * 64,
            page_count=25,
            processing_status="pending",
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        document_id = document.id

        # Verify generated values.

        assert isinstance(document.id, uuid.UUID)

        assert document.user_id == user_id

        assert document.original_filename == "data_structures.pdf"

        assert document.mime_type == "application/pdf"

        assert document.file_size_bytes == 102400

        assert document.checksum_sha256 == "a" * 64

        assert document.page_count == 25

        assert document.processing_status == "pending"

        assert document.uploaded_at is not None

        # Retrieve document.

        retrieved = db.get(Document, document_id)

        assert retrieved is not None

        assert retrieved.user.id == user_id

        # Verify reverse relationship.

        db.refresh(user)

        assert any(
            item.id == document_id
            for item in user.documents
        )

        # Verify processing status update.

        retrieved.processing_status = "processing"

        db.commit()
        db.refresh(retrieved)

        assert retrieved.processing_status == "processing"

        retrieved.processing_status = "completed"

        db.commit()
        db.refresh(retrieved)

        assert retrieved.processing_status == "completed"

        # Verify invalid processing status.

        invalid_status = Document(
            user_id=user_id,
            original_filename="invalid.pdf",
            storage_key=f"users/{user_id}/invalid/{uuid.uuid4().hex}.pdf",
            mime_type="application/pdf",
            file_size_bytes=1024,
            checksum_sha256="c" * 64,
            processing_status="unknown",
        )

        db.add(invalid_status)

        with pytest.raises(IntegrityError):
            db.commit()

        db.rollback()

        # Verify invalid file size.

        invalid_size = Document(
            user_id=user_id,
            original_filename="invalid_size.pdf",
            storage_key=f"users/{user_id}/invalid/{uuid.uuid4().hex}.pdf",
            mime_type="application/pdf",
            file_size_bytes=0,
            checksum_sha256="d" * 64,
        )

        db.add(invalid_size)

        with pytest.raises(IntegrityError):
            db.commit()

        db.rollback()

        # Verify invalid checksum.

        invalid_checksum = Document(
            user_id=user_id,
            original_filename="invalid_checksum.pdf",
            storage_key=f"users/{user_id}/invalid/{uuid.uuid4().hex}.pdf",
            mime_type="application/pdf",
            file_size_bytes=1024,
            checksum_sha256="invalid",
        )

        db.add(invalid_checksum)

        with pytest.raises(IntegrityError):
            db.commit()

        db.rollback()

        # Verify invalid page count.

        invalid_pages = Document(
            user_id=user_id,
            original_filename="invalid_pages.pdf",
            storage_key=f"users/{user_id}/invalid/{uuid.uuid4().hex}.pdf",
            mime_type="application/pdf",
            file_size_bytes=1024,
            checksum_sha256="e" * 64,
            page_count=0,
        )

        db.add(invalid_pages)

        with pytest.raises(IntegrityError):
            db.commit()

        db.rollback()

        # Verify duplicate storage key prevention.

        duplicate_storage = Document(
            user_id=user_id,
            original_filename="duplicate.pdf",
            storage_key=retrieved.storage_key,
            mime_type="application/pdf",
            file_size_bytes=1024,
            checksum_sha256="f" * 64,
        )

        db.add(duplicate_storage)

        with pytest.raises(IntegrityError):
            db.commit()

        db.rollback()

        # Verify invalid user foreign key.

        invalid_user_document = Document(
            user_id=uuid.uuid4(),
            original_filename="invalid_user.pdf",
            storage_key=f"invalid/{uuid.uuid4().hex}.pdf",
            mime_type="application/pdf",
            file_size_bytes=1024,
            checksum_sha256="1" * 64,
        )

        db.add(invalid_user_document)

        with pytest.raises(IntegrityError):
            db.commit()

        db.rollback()

        # Verify user deletion cascades to documents.

        db.execute(
            delete(User)
            .where(User.id == user_id)
            .execution_options(synchronize_session=False)
        )

        db.commit()

        assert db.get(User, user_id) is None

        assert db.get(Document, document_id) is None

    finally:

        db.rollback()

        if user_id is not None:

            remaining_user = db.get(User, user_id)

            if remaining_user is not None:
                db.delete(remaining_user)
                db.commit()

        db.close()