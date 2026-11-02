import uuid

from sqlalchemy.dialects.postgresql import JSONB

from app.database.base import Base
from app.models.user import User
from app.models.user_preferences import UserPreferences


def test_preferences_inherit_base():
    assert issubclass(UserPreferences, Base)


def test_preferences_table_name():
    assert UserPreferences.__tablename__ == "user_preferences"


def test_preferences_primary_key():
    column = UserPreferences.__table__.columns["id"]

    assert column.primary_key
    assert str(column.type) == "UUID"


def test_preferences_uuid_generation():
    generator = UserPreferences.__table__.columns["id"].default.arg

    generated_id = generator(None)

    assert isinstance(generated_id, uuid.UUID)


def test_preferences_user_foreign_key():
    column = UserPreferences.__table__.columns["user_id"]

    assert column.nullable is False

    foreign_key = next(iter(column.foreign_keys))

    assert foreign_key.target_fullname == "users.id"
    assert foreign_key.ondelete == "CASCADE"


def test_preferences_user_id_unique():
    constraints = {
        constraint.name
        for constraint in UserPreferences.__table__.constraints
    }

    assert "uq_user_preferences_user_id" in constraints


def test_preferences_language_column():
    column = UserPreferences.__table__.columns["preferred_language"]

    assert column.type.length == 10
    assert column.nullable is True


def test_preferences_education_level_column():
    column = UserPreferences.__table__.columns["education_level"]

    assert column.type.length == 50
    assert column.nullable is True


def test_preferences_subjects_column():
    column = UserPreferences.__table__.columns["preferred_subjects"]

    assert isinstance(column.type, JSONB)
    assert column.nullable is False


def test_preferences_learning_goals_column():
    column = UserPreferences.__table__.columns["learning_goals"]

    assert isinstance(column.type, JSONB)
    assert column.nullable is False


def test_preferences_notification_column():
    column = UserPreferences.__table__.columns["notification_enabled"]

    assert column.nullable is False


def test_preferences_timestamp_columns():
    created_at = UserPreferences.__table__.columns["created_at"]
    updated_at = UserPreferences.__table__.columns["updated_at"]

    assert created_at.type.timezone is True
    assert updated_at.type.timezone is True


def test_preferences_relationship():
    assert "user" in UserPreferences.__mapper__.relationships


def test_user_preferences_relationship():
    assert "preferences" in User.__mapper__.relationships

    relationship = User.__mapper__.relationships["preferences"]

    assert relationship.uselist is False


def test_preferences_instance_creation():
    preferences = UserPreferences(
        user_id=uuid.uuid4(),
        preferred_language="English",
        education_level="Undergraduate",
        preferred_subjects=["Data Structures"],
        learning_goals=["Improve programming"],
        notification_enabled=True,
    )

    assert preferences.preferred_language == "English"
    assert preferences.education_level == "Undergraduate"
    assert preferences.preferred_subjects == ["Data Structures"]
    assert preferences.learning_goals == ["Improve programming"]
    assert preferences.notification_enabled is True


def test_preferences_repr():
    preferences = UserPreferences(
        user_id=uuid.uuid4(),
        preferred_language="English",
    )

    assert "English" in repr(preferences)


def test_preferences_array_constraints():
    constraints = {
        constraint.name
        for constraint in UserPreferences.__table__.constraints
    }

    assert "ck_user_preferences_subjects_array" in constraints
    assert "ck_user_preferences_goals_array" in constraints