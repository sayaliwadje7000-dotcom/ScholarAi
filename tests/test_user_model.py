import uuid

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base
from app.models.user import User


def test_user_inherits_base():
    assert issubclass(User, Base)


def test_user_table_name():
    assert User.__tablename__ == "users"


def test_user_primary_key_type():
    column = User.__table__.c.id

    assert column.primary_key is True
    assert isinstance(column.type, UUID)


def test_user_uuid_generation():
    uuid_generator = User.__table__.c.id.default.arg

    generated_id = uuid_generator(None)

    assert isinstance(generated_id, uuid.UUID)
    assert generated_id.version == 4

def test_user_full_name_column():
    column = User.__table__.c.full_name

    assert isinstance(column.type, String)
    assert column.type.length == 150
    assert column.nullable is False


def test_user_email_column():
    column = User.__table__.c.email

    assert isinstance(column.type, String)
    assert column.type.length == 255
    assert column.nullable is False


def test_user_email_unique_constraint():
    constraints = [
        constraint
        for constraint in User.__table__.constraints
        if constraint.name == "uq_users_email"
    ]

    assert len(constraints) == 1


def test_user_email_index():
    indexes = [
        index
        for index in User.__table__.indexes
        if index.name == "ix_users_email"
    ]

    assert len(indexes) == 1


def test_user_active_column():
    column = User.__table__.c.is_active

    assert isinstance(column.type, Boolean)
    assert column.nullable is False


def test_user_timestamp_columns():
    created_at = User.__table__.c.created_at
    updated_at = User.__table__.c.updated_at

    assert isinstance(created_at.type, DateTime)
    assert isinstance(updated_at.type, DateTime)

    assert created_at.type.timezone is True
    assert updated_at.type.timezone is True


def test_user_instance_creation():
    user = User(
        full_name="ScholarAI Student",
        email="student@example.com",
    )

    assert user.full_name == "ScholarAI Student"
    assert user.email == "student@example.com"


def test_user_repr():
    user = User(
        full_name="Test User",
        email="test@example.com",
    )

    assert "test@example.com" in repr(user)