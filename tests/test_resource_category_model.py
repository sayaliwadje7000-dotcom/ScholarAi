from uuid import UUID

from sqlalchemy import CheckConstraint, UniqueConstraint

from app.database.base import Base
from app.models.resource_category import ResourceCategory


def test_resource_category_inherits_base():
    assert issubclass(ResourceCategory, Base)


def test_table_name():
    assert ResourceCategory.__tablename__ == "resource_categories"


def test_primary_key():
    assert ResourceCategory.id.property.columns[0].primary_key is True


def test_uuid_generation():
    category = ResourceCategory(
        name="Programming",
        slug="programming",
    )

    assert isinstance(category.id, UUID)


def test_name_column():
    column = ResourceCategory.name.property.columns[0]

    assert column.type.length == 100
    assert column.nullable is False


def test_slug_column():
    column = ResourceCategory.slug.property.columns[0]

    assert column.type.length == 120
    assert column.nullable is False


def test_description_column():
    assert ResourceCategory.description.property.columns[0].nullable is True


def test_parent_id_column():
    column = ResourceCategory.parent_id.property.columns[0]

    assert column.nullable is True


def test_is_active_default():
    category = ResourceCategory(
        name="Programming",
        slug="programming",
    )

    assert category.is_active is True


def test_created_at_column():
    assert ResourceCategory.created_at.property.columns[0].nullable is False


def test_updated_at_column():
    assert ResourceCategory.updated_at.property.columns[0].nullable is False


def test_model_check_constraints():
    constraint_names = {
        constraint.name
        for constraint in ResourceCategory.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    expected = {
        "ck_resource_categories_name_nonempty",
        "ck_resource_categories_slug_nonempty",
        "ck_resource_categories_slug_lowercase",
        "ck_resource_categories_no_self_parent",
    }

    assert expected.issubset(constraint_names)


def test_model_unique_constraints():
    constraint_names = {
        constraint.name
        for constraint in ResourceCategory.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    expected = {
        "uq_resource_categories_name",
        "uq_resource_categories_slug",
    }

    assert expected.issubset(constraint_names)


def test_model_indexes():
    index_names = {
        index.name
        for index in ResourceCategory.__table__.indexes
    }

    expected = {
        "ix_resource_categories_parent_id",
        "ix_resource_categories_is_active",
        "ix_resource_categories_name",
    }

    assert expected.issubset(index_names)


def test_instance_creation():
    category = ResourceCategory(
        name="Data Structures",
        slug="data-structures",
        description="Resources related to data structures.",
    )

    assert category.name == "Data Structures"
    assert category.slug == "data-structures"
    assert category.description == "Resources related to data structures."


def test_parent_child_relationships_exist():
    assert hasattr(ResourceCategory, "parent")
    assert hasattr(ResourceCategory, "children")


def test_study_resource_relationship_exists():
    assert hasattr(ResourceCategory, "study_resources")


def test_default_active_status():
    category = ResourceCategory(
        name="Mathematics",
        slug="mathematics",
    )

    assert category.is_active is True


def test_repr():
    category = ResourceCategory(
        name="Programming",
        slug="programming",
    )

    assert "ResourceCategory" in repr(category)
    assert "Programming" in repr(category)
    assert "programming" in repr(category)