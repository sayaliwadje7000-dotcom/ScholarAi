from sqlalchemy import CheckConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import configure_mappers

from app.database.base import Base
from app.models.user_resource_interaction import UserResourceInteraction


def test_model_inherits_base():
    assert issubclass(UserResourceInteraction, Base)


def test_table_name():
    assert UserResourceInteraction.__tablename__ == "user_resource_interactions"


def test_primary_key():
    column = UserResourceInteraction.__table__.c.id

    assert column.primary_key is True
    assert isinstance(column.type, UUID)


def test_uuid_generation():
    interaction = UserResourceInteraction(
        user_id=None,
        resource_id=None,
        interaction_type="view",
    )

    assert interaction.id is not None


def test_user_id_column():
    column = UserResourceInteraction.__table__.c.user_id

    assert column.nullable is False
    assert isinstance(column.type, UUID)


def test_resource_id_column():
    column = UserResourceInteraction.__table__.c.resource_id

    assert column.nullable is False
    assert isinstance(column.type, UUID)


def test_interaction_type_column():
    column = UserResourceInteraction.__table__.c.interaction_type

    assert column.nullable is False
    assert column.type.length == 30


def test_rating_column():
    column = UserResourceInteraction.__table__.c.rating

    assert column.nullable is True
    assert column.type.python_type is int


def test_duration_column():
    column = UserResourceInteraction.__table__.c.duration_seconds

    assert column.nullable is True
    assert column.type.python_type is int


def test_metadata_column():
    column = UserResourceInteraction.__table__.c["metadata"]

    assert column.nullable is False
    assert isinstance(column.type, JSONB)


def test_occurred_at_column():
    column = UserResourceInteraction.__table__.c.occurred_at

    assert column.nullable is False
    assert column.type.timezone is True


def test_default_metadata():
    interaction = UserResourceInteraction(
        user_id=None,
        resource_id=None,
        interaction_type="view",
    )

    assert interaction.interaction_metadata == {}


def test_instance_creation():
    interaction = UserResourceInteraction(
        user_id=None,
        resource_id=None,
        interaction_type="view",
        duration_seconds=120,
        interaction_metadata={"source": "search"},
    )

    assert interaction.interaction_type == "view"
    assert interaction.duration_seconds == 120
    assert interaction.interaction_metadata["source"] == "search"


def test_valid_interaction_types():
    valid_types = {
        "view",
        "click",
        "save",
        "rate",
        "complete",
    }

    constraint = next(
        constraint
        for constraint in UserResourceInteraction.__table__.constraints
        if constraint.name == "ck_user_resource_interactions_valid_type"
    )

    assert constraint is not None
    assert valid_types == {
        "view",
        "click",
        "save",
        "rate",
        "complete",
    }


def test_rating_constraint_exists():
    constraint_names = {
        constraint.name
        for constraint in UserResourceInteraction.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "ck_user_resource_interactions_valid_rating" in constraint_names


def test_duration_constraint_exists():
    constraint_names = {
        constraint.name
        for constraint in UserResourceInteraction.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "ck_user_resource_interactions_valid_duration" in constraint_names


def test_metadata_constraint_exists():
    constraint_names = {
        constraint.name
        for constraint in UserResourceInteraction.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "ck_user_resource_interactions_metadata_object" in constraint_names


def test_all_check_constraints_exist():
    constraint_names = {
        constraint.name
        for constraint in UserResourceInteraction.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    expected = {
        "ck_user_resource_interactions_valid_type",
        "ck_user_resource_interactions_valid_rating",
        "ck_user_resource_interactions_valid_duration",
        "ck_user_resource_interactions_metadata_object",
    }

    assert expected.issubset(constraint_names)


def test_all_indexes_exist():
    index_names = {
        index.name
        for index in UserResourceInteraction.__table__.indexes
    }

    expected = {
        "ix_user_resource_interactions_user_id",
        "ix_user_resource_interactions_resource_id",
        "ix_user_resource_interactions_interaction_type",
        "ix_user_resource_interactions_occurred_at",
        "ix_user_resource_interactions_user_occurred",
        "ix_user_resource_interactions_user_resource",
    }

    assert expected.issubset(index_names)


def test_foreign_keys_exist():
    foreign_keys = {
        foreign_key.parent.name: foreign_key
        for foreign_key in UserResourceInteraction.__table__.foreign_keys
    }

    assert set(foreign_keys) == {"user_id", "resource_id"}

    assert foreign_keys["user_id"].target_fullname == "users.id"
    assert foreign_keys["resource_id"].target_fullname == "study_resources.id"

    assert foreign_keys["user_id"].ondelete == "CASCADE"
    assert foreign_keys["resource_id"].ondelete == "CASCADE"


def test_user_relationship_exists():
    configure_mappers()

    assert hasattr(UserResourceInteraction, "user")
    assert UserResourceInteraction.user.property.back_populates == "resource_interactions"


def test_resource_relationship_exists():
    configure_mappers()

    assert hasattr(UserResourceInteraction, "resource")
    assert UserResourceInteraction.resource.property.back_populates == "user_interactions"


def test_repr():
    interaction = UserResourceInteraction(
        user_id=None,
        resource_id=None,
        interaction_type="view",
    )

    representation = repr(interaction)

    assert "UserResourceInteraction" in representation
    assert "view" in representation