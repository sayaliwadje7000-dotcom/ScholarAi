import os
import uuid

import pytest

from app.database.session import SessionLocal
from app.models.user import User
from app.models.document import Document

from app.services.document_status_service import (
    transition_document_status,
    get_document_processing_status,
)


pytestmark = pytest.mark.skipif(
    os.getenv("SCHOLARAI_RUN_DATABASE_INTEGRATION") != "1",
    reason="PostgreSQL integration tests are opt-in.",
)


@pytest.fixture
def db():
    session = SessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def integration_document(db):
    user = User(
        full_name="Status Integration Test",
        email=f"status-test-{uuid.uuid4()}@example.test",
    )

    db.add(user)
    db.flush()

    document = Document(
        user_id=user.id,
        original_filename="status-test.pdf",
        storage_key=f"documents/{uuid.uuid4()}.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        checksum_sha256="c" * 64,
        page_count=1,
        processing_status="pending",
        processing_attempts=0,
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    yield document

    db.rollback()

    db.query(Document).filter(
        Document.id == document.id
    ).delete(synchronize_session=False)

    db.query(User).filter(
        User.id == user.id
    ).delete(synchronize_session=False)

    db.commit()


def test_postgresql_document_status_lifecycle(
    db,
    integration_document,
):
    document_id = integration_document.id

    # pending -> processing
    processing = transition_document_status(
        db=db,
        document_id=document_id,
        new_status="processing",
    )

    assert processing.processing_status == "processing"
    assert processing.processing_attempts == 1
    assert processing.processing_started_at is not None

    # processing -> completed
    completed = transition_document_status(
        db=db,
        document_id=document_id,
        new_status="completed",
        page_count=5,
    )

    assert completed.processing_status == "completed"
    assert completed.processing_completed_at is not None
    assert completed.page_count == 5

    status = get_document_processing_status(
        db=db,
        document_id=document_id,
    )

    assert status["processing_status"] == "completed"
    assert status["processing_attempts"] == 1