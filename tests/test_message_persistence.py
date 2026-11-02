import uuid

import pytest

from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from app.database.session import SessionLocal
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message


def test_message_database_persistence():

    email = f"phase65_{uuid.uuid4().hex}@example.com"

    db = SessionLocal()

    user_id = None
    conversation_id = None
    message_id = None

    try:
        # 1. Create user.
        user = User(
            full_name="Message Test User",
            email=email,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        user_id = user.id

        # 2. Create conversation.
        conversation = Conversation(
            user_id=user_id,
            title="Database Learning",
        )

        db.add(conversation)
        db.commit()
        db.refresh(conversation)

        conversation_id = conversation.id

        # 3. Create message.
        message = Message(
            conversation_id=conversation_id,
            role="user",
            content="Explain database normalization.",
            token_count=12,
        )

        db.add(message)
        db.commit()
        db.refresh(message)

        message_id = message.id

        # 4. Verify generated fields.
        assert isinstance(message.id, uuid.UUID)
        assert message.conversation_id == conversation_id
        assert message.role == "user"
        assert message.content == "Explain database normalization."
        assert message.token_count == 12
        assert message.created_at is not None

        # 5. Retrieve message.
        retrieved = db.get(Message, message_id)

        assert retrieved is not None
        assert retrieved.content == "Explain database normalization."

        # 6. Verify conversation relationship.
        assert retrieved.conversation.id == conversation_id
        assert retrieved.conversation.user.id == user_id

        # 7. Verify reverse relationship.
        db.refresh(conversation)

        assert any(
            item.id == message_id
            for item in conversation.messages
        )

        # 8. Update message.
        retrieved.content = "Updated database normalization question."
        retrieved.token_count = 15

        db.commit()
        db.refresh(retrieved)

        assert retrieved.content == (
            "Updated database normalization question."
        )
        assert retrieved.token_count == 15

        # 9. Verify invalid role is rejected.
        invalid_role = Message(
            conversation_id=conversation_id,
            role="invalid",
            content="Invalid role test",
        )

        db.add(invalid_role)

        with pytest.raises(IntegrityError):
            db.commit()

        db.rollback()

        # 10. Verify negative token count is rejected.
        invalid_tokens = Message(
            conversation_id=conversation_id,
            role="user",
            content="Invalid token count test",
            token_count=-5,
        )

        db.add(invalid_tokens)

        with pytest.raises(IntegrityError):
            db.commit()

        db.rollback()

        # 11. Verify invalid conversation reference is rejected.
        invalid_conversation = Message(
            conversation_id=uuid.uuid4(),
            role="user",
            content="Invalid conversation test",
        )

        db.add(invalid_conversation)

        with pytest.raises(IntegrityError):
            db.commit()

        db.rollback()

        # 12. Verify database cascade deletion.
        db.execute(
            delete(User)
            .where(User.id == user_id)
            .execution_options(synchronize_session=False)
        )

        db.commit()

        assert db.get(User, user_id) is None
        assert db.get(Conversation, conversation_id) is None
        assert db.get(Message, message_id) is None

    finally:
        db.rollback()

        if user_id is not None:
            remaining_user = db.get(User, user_id)

            if remaining_user is not None:
                db.delete(remaining_user)
                db.commit()

        db.close()