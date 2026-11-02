import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import configure_mappers

from app.database.base import Base
from app.models import User, Conversation


def test_conversation_inherits_base():
    assert issubclass(Conversation, Base)


def test_conversation_table_name():
    assert Conversation.__tablename__ == "conversations"


def test_conversation_primary_key():
    column = Conversation.__table__.c.id

    assert column.primary_key is True
    assert isinstance(column.type, UUID)


def test_conversation_uuid_generation():
    uuid_generator = Conversation.__table__.c.id.default.arg

    generated_id = uuid_generator(None)

    assert isinstance(generated_id, uuid.UUID)
    assert generated_id.version == 4


def test_conversation_user_id_foreign_key():
    column = Conversation.__table__.c.user_id

    assert column.nullable is False
    assert isinstance(column.type, UUID)

    foreign_keys = list(column.foreign_keys)

    assert len(foreign_keys) == 1
    assert foreign_keys[0].target_fullname == "users.id"
    assert foreign_keys[0].ondelete == "CASCADE"


def test_conversation_title_column():
    column = Conversation.__table__.c.title

    assert isinstance(column.type, String)
    assert column.type.length == 200
    assert column.nullable is True


def test_conversation_archive_column():
    column = Conversation.__table__.c.is_archived

    assert isinstance(column.type, Boolean)
    assert column.nullable is False


def test_conversation_timestamp_columns():
    created_at = Conversation.__table__.c.created_at
    updated_at = Conversation.__table__.c.updated_at

    assert isinstance(created_at.type, DateTime)
    assert isinstance(updated_at.type, DateTime)

    assert created_at.type.timezone is True
    assert updated_at.type.timezone is True


def test_conversation_user_relationship():
    configure_mappers()

    user_relationship = Conversation.__mapper__.relationships["user"]

    assert user_relationship.mapper.class_ is User
    assert user_relationship.back_populates == "conversations"


def test_user_conversations_relationship():
    configure_mappers()

    relationship = User.__mapper__.relationships["conversations"]

    assert relationship.mapper.class_ is Conversation
    assert relationship.back_populates == "user"


def test_conversation_instance_creation():
    conversation = Conversation(
        user_id=uuid.uuid4(),
        title="Data Structures",
    )

    assert conversation.title == "Data Structures"
    assert conversation.is_archived is None


def test_conversation_indexes():
    indexes = {
        index.name
        for index in Conversation.__table__.indexes
    }

    assert "ix_conversations_user_id" in indexes
    assert "ix_conversations_user_updated" in indexes