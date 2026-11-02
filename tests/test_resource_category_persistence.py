from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.database.session import SessionLocal
from app.models.resource_category import ResourceCategory
from app.models.study_resource import StudyResource
from app.models.study_resource_category import study_resource_categories


@pytest.fixture
def db_session():
    session = SessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


def unique_value(prefix):
    return f"{prefix}-{uuid4().hex[:12]}"


def create_category(db_session, name_prefix="Category"):
    unique = uuid4().hex[:12]

    category = ResourceCategory(
        name=f"{name_prefix} {unique}",
        slug=f"{name_prefix.lower()}-{unique}",
    )

    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)

    return category


def create_resource(db_session):
    resource = StudyResource(
        title=f"Test Resource {uuid4().hex[:12]}",
        resource_type="tutorial",
        url=f"https://example.com/{uuid4().hex}",
    )

    db_session.add(resource)
    db_session.commit()
    db_session.refresh(resource)

    return resource


def test_resource_category_database_persistence(db_session):
    unique = uuid4().hex[:12]

    category = ResourceCategory(
        name=f"Programming {unique}",
        slug=f"programming-{unique}",
        description="Programming study resources.",
    )

    db_session.add(category)
    db_session.commit()

    category_id = category.id

    retrieved = db_session.execute(
        select(ResourceCategory).where(
            ResourceCategory.id == category_id
        )
    ).scalar_one()

    assert retrieved.name == f"Programming {unique}"
    assert retrieved.slug == f"programming-{unique}"
    assert retrieved.description == "Programming study resources."
    assert retrieved.is_active is True


def test_duplicate_category_name_rejected(db_session):
    category = create_category(db_session)

    duplicate = ResourceCategory(
        name=category.name,
        slug=unique_value("different-slug"),
    )

    db_session.add(duplicate)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_duplicate_category_slug_rejected(db_session):
    category = create_category(db_session)

    duplicate = ResourceCategory(
        name=unique_value("Different Category"),
        slug=category.slug,
    )

    db_session.add(duplicate)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


@pytest.mark.parametrize("name", ["", "   "])
def test_empty_category_name_rejected(db_session, name):
    category = ResourceCategory(
        name=name,
        slug=unique_value("valid-slug"),
    )

    db_session.add(category)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


@pytest.mark.parametrize("slug", ["", "   ", "INVALID-SLUG"])
def test_invalid_category_slug_rejected(db_session, slug):
    category = ResourceCategory(
        name=unique_value("Valid Category"),
        slug=slug,
    )

    db_session.add(category)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_parent_child_category_relationship(db_session):
    parent = create_category(db_session, "Programming")

    child = ResourceCategory(
        name=unique_value("Python"),
        slug=unique_value("python"),
        parent_id=parent.id,
    )

    db_session.add(child)
    db_session.commit()

    db_session.refresh(parent)
    db_session.refresh(child)

    assert child.parent_id == parent.id
    assert child.parent.id == parent.id
    assert any(item.id == child.id for item in parent.children)


def test_category_can_be_assigned_to_resource(db_session):
    category = create_category(db_session)
    resource = create_resource(db_session)

    resource.categories.append(category)
    db_session.commit()

    db_session.expire(resource, ["categories"])

    assert any(
        item.id == category.id
        for item in resource.categories
    )


def test_resource_can_have_multiple_categories(db_session):
    resource = create_resource(db_session)

    category_one = create_category(db_session, "Programming")
    category_two = create_category(db_session, "Mathematics")

    resource.categories.extend([category_one, category_two])
    db_session.commit()

    db_session.expire(resource, ["categories"])

    category_ids = {
        category.id for category in resource.categories
    }

    assert category_ids == {
        category_one.id,
        category_two.id,
    }


def test_duplicate_resource_category_assignment_rejected(db_session):
    from sqlalchemy import insert

    resource = create_resource(db_session)
    category = create_category(db_session)

    association = study_resource_categories

    values = {
        "resource_id": resource.id,
        "category_id": category.id,
    }

    db_session.execute(insert(association).values(**values))
    db_session.commit()

    with pytest.raises(IntegrityError):
        db_session.execute(insert(association).values(**values))
        db_session.commit()

    db_session.rollback()

def test_association_has_assigned_at_timestamp(db_session):
    resource = create_resource(db_session)
    category = create_category(db_session)

    resource.categories.append(category)
    db_session.commit()

    result = db_session.execute(
        select(study_resource_categories.c.assigned_at).where(
            study_resource_categories.c.resource_id == resource.id,
            study_resource_categories.c.category_id == category.id,
        )
    ).scalar_one()

    assert result is not None


def test_category_deletion_cascades_association(db_session):
    resource = create_resource(db_session)
    category = create_category(db_session)

    resource.categories.append(category)
    db_session.commit()

    resource_id = resource.id
    category_id = category.id

    db_session.execute(
        delete(ResourceCategory).where(
            ResourceCategory.id == category_id
        )
    )
    db_session.commit()

    association = db_session.execute(
        select(study_resource_categories).where(
            study_resource_categories.c.resource_id == resource_id,
            study_resource_categories.c.category_id == category_id,
        )
    ).first()

    assert association is None


def test_resource_deletion_cascades_association(db_session):
    resource = create_resource(db_session)
    category = create_category(db_session)

    resource.categories.append(category)
    db_session.commit()

    resource_id = resource.id
    category_id = category.id

    db_session.execute(
        delete(StudyResource).where(
            StudyResource.id == resource_id
        )
    )
    db_session.commit()

    association = db_session.execute(
        select(study_resource_categories).where(
            study_resource_categories.c.resource_id == resource_id,
            study_resource_categories.c.category_id == category_id,
        )
    ).first()

    assert association is None


def test_parent_category_deletion_restricted(db_session):
    parent = create_category(db_session, "Parent")

    child = ResourceCategory(
        name=unique_value("Child"),
        slug=unique_value("child"),
        parent_id=parent.id,
    )

    db_session.add(child)
    db_session.commit()

    with pytest.raises(IntegrityError):
        db_session.execute(
            delete(ResourceCategory).where(
                ResourceCategory.id == parent.id
            )
        )
        db_session.commit()

    db_session.rollback()


def test_inactive_category_can_be_stored(db_session):
    category = ResourceCategory(
        name=unique_value("Archived"),
        slug=unique_value("archived"),
        is_active=False,
    )

    db_session.add(category)
    db_session.commit()

    assert category.is_active is False