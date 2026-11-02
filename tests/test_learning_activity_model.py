import uuid

from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database.base import Base
from app.models.user import User
from app.models.learning_activity import LearningActivity


def test_learning_activity_inherits_base():
    assert issubclass(LearningActivity, Base)


def test_learning_activity_table_name():
    assert LearningActivity.__tablename__ == "learning_activities"


def test_learning_activity_primary_key():
    column = LearningActivity.__table__.columns["id"]

    assert column.primary_key
    assert isinstance(column.type, UUID)


def test_learning_activity_uuid_generation():
    generator = LearningActivity.__table__.columns["id"].default.arg

    assert isinstance(generator(None), uuid.UUID)


def test_learning_activity_user_foreign_key():
    column = LearningActivity.__table__.columns["user_id"]

    assert column.nullable is False

    foreign_key = next(iter(column.foreign_keys))

    assert foreign_key.target_fullname == "users.id"
    assert foreign_key.ondelete == "CASCADE"


def test_activity_type_column():
    column = LearningActivity.__table__.columns["activity_type"]

    assert column.type.length == 50
    assert column.nullable is False


def test_entity_type_column():
    column = LearningActivity.__table__.columns["entity_type"]

    assert column.type.length == 50
    assert column.nullable is True


def test_entity_id_column():
    column = LearningActivity.__table__.columns["entity_id"]

    assert isinstance(column.type, UUID)
    assert column.nullable is True


def test_duration_column():
    column = LearningActivity.__table__.columns["duration_seconds"]

    assert str(column.type) == "INTEGER"
    assert column.nullable is True


def test_metadata_column():
    column = LearningActivity.__table__.columns["metadata"]

    assert isinstance(column.type, JSONB)
    assert column.nullable is False


def test_metadata_python_attribute():
    assert hasattr(LearningActivity, "activity_metadata")


def test_occurred_at_column():
    column = LearningActivity.__table__.columns["occurred_at"]

    assert column.type.timezone is True
    assert column.nullable is False


def test_user_relationship():
    assert "user" in LearningActivity.__mapper__.relationships


def test_user_learning_activities_relationship():
    assert "learning_activities" in User.__mapper__.relationships

    relationship = User.__mapper__.relationships[
        "learning_activities"
    ]

    assert relationship.uselist is True


def test_learning_activity_constraints():
    constraints = {
        constraint.name
        for constraint in LearningActivity.__table__.constraints
    }

    assert (
        "ck_learning_activities_nonempty_activity_type"
        in constraints
    )

    assert (
        "ck_learning_activities_valid_entity_type"
        in constraints
    )

    assert (
        "ck_learning_activities_entity_reference_pair"
        in constraints
    )

    assert (
        "ck_learning_activities_nonnegative_duration"
        in constraints
    )


def test_learning_activity_indexes():
    indexes = {
        index.name
        for index in LearningActivity.__table__.indexes
    }

    assert "ix_learning_activities_user_id" in indexes
    assert "ix_learning_activities_occurred_at" in indexes
    assert "ix_learning_activities_user_occurred" in indexes
    assert "ix_learning_activities_entity" in indexes


def test_learning_activity_instance_creation():
    activity = LearningActivity(
        user_id=uuid.uuid4(),
        activity_type="document_upload",
        entity_type="document",
        entity_id=uuid.uuid4(),
        duration_seconds=15,
        activity_metadata={
            "filename": "data_structures.pdf",
            "pages": 25,
        },
    )

    assert activity.activity_type == "document_upload"
    assert activity.entity_type == "document"
    assert isinstance(activity.entity_id, uuid.UUID)
    assert activity.duration_seconds == 15

    assert activity.activity_metadata["filename"] == (
        "data_structures.pdf"
    )


def test_learning_activity_without_entity():
    activity = LearningActivity(
        user_id=uuid.uuid4(),
        activity_type="study_session",
        activity_metadata={},
    )

    assert activity.entity_type is None
    assert activity.entity_id is None


def test_learning_activity_repr():
    activity = LearningActivity(
        user_id=uuid.uuid4(),
        activity_type="quiz_attempt",
        entity_type="quiz",
        entity_id=uuid.uuid4(),
    )

    assert "quiz_attempt" in repr(activity)