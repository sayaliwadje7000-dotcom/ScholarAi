import uuid

import pytest
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from app.database.session import SessionLocal
from app.models.user import User
from app.models.conversation import Conversation


def test_conversation_database_persistence():
    email = f"phase64_{uuid.uuid4().hex}@example.com"

    db = SessionLocal()
    user_id = None
    conversation_id = None

    try:
        # Create user
        user = User(
            full_name="Conversation Test User",
            email=email,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        user_id = user.id

        # Create conversation
        conversation = Conversation(
            user_id=user_id,
            title="Data Structures Study",
        )

        db.add(conversation)
        db.commit()
        db.refresh(conversation)

        conversation_id = conversation.id

        # Verify generated fields
        assert isinstance(conversation.id, uuid.UUID)
        assert conversation.user_id == user_id
        assert conversation.is_archived is False
        assert conversation.created_at is not None
        assert conversation.updated_at is not None

        # Retrieve conversation
        retrieved = db.get(Conversation, conversation_id)

        assert retrieved is not None
        assert retrieved.title == "Data Structures Study"

        # Verify user relationship
        assert retrieved.user.id == user_id
        assert retrieved.user.email == email

        # Update conversation
        retrieved.title = "Updated Data Structures Study"

        db.commit()
        db.refresh(retrieved)

        assert retrieved.title == "Updated Data Structures Study"

        # Verify foreign-key enforcement
        invalid_conversation = Conversation(
            user_id=uuid.uuid4(),
            title="Invalid Conversation",
        )

        db.add(invalid_conversation)

        with pytest.raises(IntegrityError):
            db.commit()

        db.rollback()

        # Delete user and verify database cascade
        db.execute(
            delete(User)
            .where(User.id == user_id)
            .execution_options(synchronize_session=False)
        )

        db.commit()

        assert db.get(User, user_id) is None
        assert db.get(Conversation, conversation_id) is None

    finally:
        db.rollback()

        if user_id is not None:
            remaining_user = db.get(User, user_id)

            if remaining_user is not None:
                db.delete(remaining_user)
                db.commit()

        db.close()