import uuid

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index

from app.database.base import Base
from app.models.message import Message
from app.models.conversation import Conversation


def test_message_inherits_base():
    assert issubclass(Message, Base)


def test_message_table_name():
    assert Message.__tablename__ == "messages"


def test_message_primary_key():
    column = Message.__table__.columns["id"]

    assert column.primary_key
    assert str(column.type) == "UUID"


def test_message_uuid_generation():
    generator = Message.__table__.columns["id"].default.arg

    generated_id = generator(None)

    assert isinstance(generated_id, uuid.UUID)


def test_message_conversation_foreign_key():
    column = Message.__table__.columns["conversation_id"]

    assert column.nullable is False

    foreign_key = next(iter(column.foreign_keys))

    assert foreign_key.target_fullname == "conversations.id"
    assert foreign_key.ondelete == "CASCADE"


def test_message_role_column():
    column = Message.__table__.columns["role"]

    assert column.nullable is False
    assert column.type.length == 20


def test_message_content_column():
    column = Message.__table__.columns["content"]

    assert column.nullable is False
    assert str(column.type) == "TEXT"


def test_message_token_count_column():
    column = Message.__table__.columns["token_count"]

    assert column.nullable is True
    assert str(column.type) == "INTEGER"


def test_message_timestamp_column():
    column = Message.__table__.columns["created_at"]

    assert column.nullable is False
    assert column.type.timezone is True


def test_message_relationship():
    assert "conversation" in Message.__mapper__.relationships


def test_conversation_messages_relationship():
    assert "messages" in Conversation.__mapper__.relationships


def test_message_constraints():
    constraints = {
        constraint.name
        for constraint in Message.__table__.constraints
    }

    assert "ck_messages_valid_role" in constraints
    assert "ck_messages_nonnegative_token_count" in constraints


def test_message_indexes():
    indexes = {
        index.name
        for index in Message.__table__.indexes
    }

    assert "ix_messages_conversation_created" in indexes


def test_message_instance_creation():
    message = Message(
        conversation_id=uuid.uuid4(),
        role="user",
        content="Explain binary search trees.",
    )

    assert message.role == "user"
    assert message.content == "Explain binary search trees."
    assert message.token_count is None


def test_message_repr():
    message = Message(
        conversation_id=uuid.uuid4(),
        role="assistant",
        content="A binary search tree is...",
    )

    assert "assistant" in repr(message)