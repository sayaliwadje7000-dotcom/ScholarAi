import os
import uuid

import pytest

from sqlalchemy import select

from app.database.session import SessionLocal
from app.models.document import Document
from app.models.user import User

from app.services.document_database_service import (
    create_document_record,
    get_document_by_id,
    get_user_document,
    list_user_documents,
    count_user_documents,
)

from app.services.document_storage_service import StoredDocument


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
def integration_user(db):
    user = User(
        full_name="ScholarAI Integration Test",
        email=f"document-test-{uuid.uuid4()}@example.test",
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    yield user

    db.rollback()

    db.query(Document).filter(
        Document.user_id == user.id
    ).delete(synchronize_session=False)

    db.delete(user)
    db.commit()


def test_document_database_postgresql_round_trip(
    db,
    integration_user,
):
    stored = StoredDocument(
        document_id=uuid.uuid4(),
        storage_key=f"documents/{uuid.uuid4()}.pdf",
        original_filename="integration-test.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        checksum_sha256="b" * 64,
        page_count=3,
    )

    created = create_document_record(
        db=db,
        user_id=integration_user.id,
        stored_document=stored,
    )

    assert created.id == stored.document_id

    retrieved = get_document_by_id(
        db=db,
        document_id=stored.document_id,
    )

    assert retrieved.user_id == integration_user.id
    assert retrieved.checksum_sha256 == "b" * 64

    owned = get_user_document(
        db=db,
        document_id=stored.document_id,
        user_id=integration_user.id,
    )

    assert owned.id == stored.document_id

    listed = list_user_documents(
        db=db,
        user_id=integration_user.id,
    )

    assert any(
        item.id == stored.document_id
        for item in listed
    )

    assert count_user_documents(
        db=db,
        user_id=integration_user.id,
    ) >= 1

    db.delete(created)
    db.commit()