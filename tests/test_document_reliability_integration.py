import os
import uuid

import pytest

from sqlalchemy import text

from app.database.session import SessionLocal
from app.models.user import User
from app.models.document import Document

from app.services.document_status_service import (
    transition_document_status,
    get_document_processing_status,
    claim_document_for_processing,
    DocumentAlreadyClaimedError,
)


# ============================================================
# DATABASE INTEGRATION TEST CONFIGURATION
# ============================================================

pytestmark = pytest.mark.skipif(
    os.getenv("SCHOLARAI_RUN_DATABASE_INTEGRATION") != "1",
    reason="PostgreSQL integration tests are opt-in.",
)


# ============================================================
# DATABASE FIXTURES
# ============================================================

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
        full_name="Reliability Integration Test",
        email=f"reliability-{uuid.uuid4()}@example.test",
    )

    db.add(user)
    db.flush()

    document = Document(
        user_id=user.id,
        original_filename="reliability-test.pdf",
        storage_key=f"documents/{uuid.uuid4()}.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        checksum_sha256="d" * 64,
        page_count=1,
        processing_status="pending",
        processing_attempts=0,
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    yield document

    document_id = document.id
    user_id = user.id

    db.rollback()

    db.query(Document).filter(
        Document.id == document_id
    ).delete(synchronize_session=False)

    db.query(User).filter(
        User.id == user_id
    ).delete(synchronize_session=False)

    db.commit()


# ============================================================
# 1. DATABASE CONNECTIVITY
# ============================================================

def test_postgresql_connection(db):

    result = db.execute(
        text("SELECT 1")
    ).scalar()

    assert result == 1


# ============================================================
# 2. DOCUMENT PERSISTENCE
# ============================================================

def test_document_persists_in_postgresql(
    db,
    integration_document,
):

    stored_document = db.get(
        Document,
        integration_document.id,
    )

    assert stored_document is not None

    assert stored_document.original_filename == (
        "reliability-test.pdf"
    )

    assert stored_document.processing_status == "pending"

    assert stored_document.processing_attempts == 0


# ============================================================
# 3. PROCESSING LIFECYCLE
# ============================================================

def test_complete_document_processing_lifecycle(
    db,
    integration_document,
):

    document_id = integration_document.id

    # Pending -> Processing

    processing = transition_document_status(
        db=db,
        document_id=document_id,
        new_status="processing",
    )

    assert processing.processing_status == "processing"

    assert processing.processing_attempts == 1

    assert processing.processing_started_at is not None

    # Processing -> Completed

    completed = transition_document_status(
        db=db,
        document_id=document_id,
        new_status="completed",
        page_count=5,
    )

    assert completed.processing_status == "completed"

    assert completed.processing_completed_at is not None

    assert completed.page_count == 5

    # Verify persisted state using a fresh session.

    with SessionLocal() as verification_db:

        persisted = verification_db.get(
            Document,
            document_id,
        )

        assert persisted.processing_status == "completed"

        assert persisted.processing_attempts == 1

        assert persisted.page_count == 5


# ============================================================
# 4. FAILURE AND RECOVERY
# ============================================================

def test_failed_document_can_be_reprocessed(
    db,
    integration_document,
):

    document_id = integration_document.id

    # First attempt.

    transition_document_status(
        db=db,
        document_id=document_id,
        new_status="processing",
    )

    transition_document_status(
        db=db,
        document_id=document_id,
        new_status="failed",
        error_message="Temporary OCR failure.",
    )

    # Retry.

    retried = transition_document_status(
        db=db,
        document_id=document_id,
        new_status="processing",
    )

    assert retried.processing_status == "processing"

    assert retried.processing_attempts == 2

    assert retried.processing_error is None


# ============================================================
# 5. ATOMIC DOCUMENT CLAIM
# ============================================================

def test_document_can_be_claimed_once(
    db,
    integration_document,
):

    document_id = integration_document.id

    claimed = claim_document_for_processing(
        db=db,
        document_id=document_id,
    )

    assert claimed.processing_status == "processing"

    assert claimed.processing_attempts == 1

    # A second independent session must not claim
    # the same already-processing document.

    with SessionLocal() as second_session:

        with pytest.raises(DocumentAlreadyClaimedError):

            claim_document_for_processing(
                db=second_session,
                document_id=document_id,
            )


# ============================================================
# 6. RETRY ATTEMPT PERSISTENCE
# ============================================================

def test_retry_attempt_counter_persists(
    db,
    integration_document,
):

    document_id = integration_document.id

    # Attempt 1.

    transition_document_status(
        db=db,
        document_id=document_id,
        new_status="processing",
    )

    transition_document_status(
        db=db,
        document_id=document_id,
        new_status="failed",
        error_message="First attempt failed.",
    )

    # Attempt 2.

    transition_document_status(
        db=db,
        document_id=document_id,
        new_status="processing",
    )

    transition_document_status(
        db=db,
        document_id=document_id,
        new_status="failed",
        error_message="Second attempt failed.",
    )

    with SessionLocal() as verification_db:

        persisted = verification_db.get(
            Document,
            document_id,
        )

        assert persisted.processing_attempts == 2

        assert persisted.processing_status == "failed"

        assert persisted.processing_error == (
            "Second attempt failed."
        )


# ============================================================
# 7. STATUS RETRIEVAL AFTER PERSISTENCE
# ============================================================

def test_status_api_service_reads_persisted_document(
    db,
    integration_document,
):

    document_id = integration_document.id

    transition_document_status(
        db=db,
        document_id=document_id,
        new_status="processing",
    )

    transition_document_status(
        db=db,
        document_id=document_id,
        new_status="completed",
        page_count=8,
    )

    result = get_document_processing_status(
        db=db,
        document_id=document_id,
    )

    assert result["document_id"] == str(document_id)

    assert result["processing_status"] == "completed"

    assert result["processing_attempts"] == 1

    assert result["page_count"] == 8


# ============================================================
# 8. INVALID TRANSITION AFTER PERSISTENCE
# ============================================================

def test_completed_document_cannot_be_claimed_again(
    db,
    integration_document,
):

    document_id = integration_document.id

    transition_document_status(
        db=db,
        document_id=document_id,
        new_status="processing",
    )

    transition_document_status(
        db=db,
        document_id=document_id,
        new_status="completed",
        page_count=4,
    )

    with SessionLocal() as second_session:

        with pytest.raises(DocumentAlreadyClaimedError):

            claim_document_for_processing(
                db=second_session,
                document_id=document_id,
            )

    with SessionLocal() as verification_db:

        persisted = verification_db.get(
            Document,
            document_id,
        )

        assert persisted.processing_status == "completed"

        assert persisted.processing_attempts == 1