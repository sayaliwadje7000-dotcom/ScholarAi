from sqlalchemy import inspect
from sqlalchemy.orm import configure_mappers

import app.models

from app.database.base import Base
from app.database.session import engine


EXPECTED_TABLES = {
    "users",
    "user_preferences",
    "conversations",
    "messages",
    "documents",
    "learning_activities",
    "study_resources",
    "resource_categories",
    "study_resource_categories",
    "user_resource_interactions",
    "recommendations",
    "recommendation_feedback",
}


def test_all_expected_models_registered():
    assert EXPECTED_TABLES.issubset(
        set(Base.metadata.tables.keys())
    )


def test_all_expected_database_tables_exist():
    inspector = inspect(engine)

    assert EXPECTED_TABLES.issubset(
        set(inspector.get_table_names())
    )


def test_all_relationships_configure():
    configure_mappers()


def test_all_tables_have_primary_keys():
    inspector = inspect(engine)

    for table in EXPECTED_TABLES:
        primary_key = inspector.get_pk_constraint(table)

        assert primary_key["constrained_columns"], (
            f"{table} has no primary key"
        )


def test_foreign_keys_reference_existing_tables():
    inspector = inspect(engine)

    for table in EXPECTED_TABLES:
        for foreign_key in inspector.get_foreign_keys(table):
            assert foreign_key["referred_table"] in EXPECTED_TABLES


def test_recommendation_feedback_unique_constraint():
    table = Base.metadata.tables["recommendation_feedback"]

    unique_constraints = [
        tuple(constraint.columns.keys())
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    ]

    assert ("recommendation_id",) in unique_constraints


def test_feedback_foreign_key_cascade():
    table = Base.metadata.tables["recommendation_feedback"]

    foreign_key = next(
        fk
        for fk in table.foreign_keys
        if fk.parent.name == "recommendation_id"
    )

    assert foreign_key.ondelete == "CASCADE"


def test_recommendation_foreign_keys():
    table = Base.metadata.tables["recommendations"]

    foreign_keys = {
        fk.parent.name: fk
        for fk in table.foreign_keys
    }

    assert foreign_keys["user_id"].ondelete == "CASCADE"
    assert foreign_keys["resource_id"].ondelete == "CASCADE"


def test_association_table_composite_primary_key():
    table = Base.metadata.tables["study_resource_categories"]

    columns = tuple(
        column.name
        for column in table.primary_key.columns
    )

    assert columns == ("resource_id", "category_id")


def test_recommendation_feedback_relationship():
    from app.models.recommendation import Recommendation

    assert (
        "feedback_entries"
        in Recommendation.__mapper__.relationships
    )


def test_recommendation_feedback_has_no_duplicate_fk_index():
    table = Base.metadata.tables["recommendation_feedback"]

    indexes = {
        index.name
        for index in table.indexes
    }

    assert (
        "ix_recommendation_feedback_recommendation_id"
        not in indexes
    )


def test_user_email_has_unique_constraint():
    table = Base.metadata.tables["users"]

    unique_constraints = [
        tuple(constraint.columns.keys())
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    ]

    assert ("email",) in unique_constraints


def test_query_loading_helpers_import():
    from app.database.query_options import (
        user_dashboard_options,
        study_resource_options,
        recommendation_options,
    )

    assert callable(user_dashboard_options)
    assert callable(study_resource_options)
    assert callable(recommendation_options)