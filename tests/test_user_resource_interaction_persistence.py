import json
from uuid import uuid4

import pytest

from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError

from app.database.session import SessionLocal
from app.models.user import User
from app.models.study_resource import StudyResource
from app.models.user_resource_interaction import UserResourceInteraction


@pytest.fixture
def db_session():
    session = SessionLocal()

    user_ids = []
    resource_ids = []

    session.info["test_user_ids"] = user_ids
    session.info["test_resource_ids"] = resource_ids

    try:
        yield session

    finally:
        session.rollback()

        # Remove test records created by this fixture.
        try:
            for user_id in user_ids:
                session.execute(
                    delete(User).where(User.id == user_id)
                )

            for resource_id in resource_ids:
                session.execute(
                    delete(StudyResource).where(
                        StudyResource.id == resource_id
                    )
                )

            session.commit()

        except Exception:
            session.rollback()
            raise

        finally:
            session.close()


def create_user(db_session):
    user = User(
        full_name="ScholarAI Test User",
        email=f"test_{uuid4().hex}@example.com",
    )

    db_session.add(user)
    db_session.flush()

    db_session.info["test_user_ids"].append(user.id)

    return user


def create_resource(db_session):
    resource = StudyResource(
        title="Test Educational Resource",
        resource_type="tutorial",
        url=f"https://example.com/resource/{uuid4().hex}",
        provider="Test Provider",
        subject="Computer Science",
    )

    db_session.add(resource)
    db_session.flush()

    db_session.info["test_resource_ids"].append(resource.id)

    return resource


def create_interaction(
    db_session,
    user,
    resource,
    interaction_type="view",
    rating=None,
    duration_seconds=None,
    interaction_metadata=None,
):
    interaction = UserResourceInteraction(
        user_id=user.id,
        resource_id=resource.id,
        interaction_type=interaction_type,
        rating=rating,
        duration_seconds=duration_seconds,
        interaction_metadata=interaction_metadata or {},
    )

    db_session.add(interaction)

    return interaction


def test_interaction_database_persistence(db_session):
    user = create_user(db_session)
    resource = create_resource(db_session)

    interaction = create_interaction(
        db_session,
        user,
        resource,
        interaction_type="view",
        duration_seconds=120,
        interaction_metadata={
            "source": "search",
            "device": "desktop",
        },
    )

    db_session.commit()

    interaction_id = interaction.id

    retrieved = db_session.execute(
        select(UserResourceInteraction).where(
            UserResourceInteraction.id == interaction_id
        )
    ).scalar_one()

    assert retrieved.user_id == user.id
    assert retrieved.resource_id == resource.id
    assert retrieved.interaction_type == "view"
    assert retrieved.duration_seconds == 120
    assert retrieved.interaction_metadata["source"] == "search"
    assert retrieved.interaction_metadata["device"] == "desktop"
    assert retrieved.occurred_at is not None


@pytest.mark.parametrize(
    "interaction_type,rating",
    [
        ("view", None),
        ("click", None),
        ("save", None),
        ("rate", 5),
        ("complete", None),
    ],
)
def test_valid_interaction_types_persist(
    db_session,
    interaction_type,
    rating,
):
    user = create_user(db_session)
    resource = create_resource(db_session)

    interaction = create_interaction(
        db_session,
        user,
        resource,
        interaction_type=interaction_type,
        rating=rating,
    )

    db_session.commit()

    retrieved = db_session.get(
        UserResourceInteraction,
        interaction.id,
    )

    assert retrieved is not None
    assert retrieved.interaction_type == interaction_type


@pytest.mark.parametrize(
    "interaction_type",
    ["invalid", "random", ""],
)
def test_invalid_interaction_type_rejected(
    db_session,
    interaction_type,
):
    user = create_user(db_session)
    resource = create_resource(db_session)

    interaction = create_interaction(
        db_session,
        user,
        resource,
        interaction_type=interaction_type,
    )

    db_session.add(interaction)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


@pytest.mark.parametrize(
    "rating",
    [0, 6, -1],
)
def test_invalid_rating_rejected(db_session, rating):
    user = create_user(db_session)
    resource = create_resource(db_session)

    interaction = create_interaction(
        db_session,
        user,
        resource,
        interaction_type="rate",
        rating=rating,
    )

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_rating_required_for_rate_interaction(db_session):
    user = create_user(db_session)
    resource = create_resource(db_session)

    create_interaction(
        db_session,
        user,
        resource,
        interaction_type="rate",
        rating=None,
    )

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_rating_not_allowed_for_view_interaction(db_session):
    user = create_user(db_session)
    resource = create_resource(db_session)

    create_interaction(
        db_session,
        user,
        resource,
        interaction_type="view",
        rating=5,
    )

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_negative_duration_rejected(db_session):
    user = create_user(db_session)
    resource = create_resource(db_session)

    create_interaction(
        db_session,
        user,
        resource,
        interaction_type="view",
        duration_seconds=-10,
    )

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_zero_duration_allowed(db_session):
    user = create_user(db_session)
    resource = create_resource(db_session)

    interaction = create_interaction(
        db_session,
        user,
        resource,
        duration_seconds=0,
    )

    db_session.commit()

    retrieved = db_session.get(
        UserResourceInteraction,
        interaction.id,
    )

    assert retrieved.duration_seconds == 0


def test_metadata_must_be_json_object(db_session):
    user = create_user(db_session)
    resource = create_resource(db_session)

    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                """
                INSERT INTO user_resource_interactions (
                    id,
                    user_id,
                    resource_id,
                    interaction_type,
                    metadata
                )
                VALUES (
                    :id,
                    :user_id,
                    :resource_id,
                    'view',
                    CAST(:metadata AS jsonb)
                )
                """
            ),
            {
                "id": str(uuid4()),
                "user_id": str(user.id),
                "resource_id": str(resource.id),
                "metadata": json.dumps(["invalid", "metadata"]),
            },
        )

        db_session.commit()

    db_session.rollback()


def test_multiple_interactions_for_same_resource_allowed(db_session):
    user = create_user(db_session)
    resource = create_resource(db_session)

    first = create_interaction(
        db_session,
        user,
        resource,
        interaction_type="view",
    )

    second = create_interaction(
        db_session,
        user,
        resource,
        interaction_type="click",
    )

    third = create_interaction(
        db_session,
        user,
        resource,
        interaction_type="save",
    )

    db_session.commit()

    interactions = db_session.execute(
        select(UserResourceInteraction).where(
            UserResourceInteraction.user_id == user.id,
            UserResourceInteraction.resource_id == resource.id,
        )
    ).scalars().all()

    assert len(interactions) == 3

    assert {
        interaction.id
        for interaction in interactions
    } == {
        first.id,
        second.id,
        third.id,
    }


def test_user_resource_relationships(db_session):
    user = create_user(db_session)
    resource = create_resource(db_session)

    interaction = create_interaction(
        db_session,
        user,
        resource,
        interaction_type="view",
    )

    db_session.commit()

    db_session.refresh(user)
    db_session.refresh(resource)

    assert interaction.user.id == user.id
    assert interaction.resource.id == resource.id

    assert any(
        item.id == interaction.id
        for item in user.resource_interactions
    )

    assert any(
        item.id == interaction.id
        for item in resource.user_interactions
    )


def test_user_deletion_cascades_interactions(db_session):
    user = create_user(db_session)
    resource = create_resource(db_session)

    interaction = create_interaction(
        db_session,
        user,
        resource,
    )

    db_session.commit()

    interaction_id = interaction.id
    user_id = user.id

    db_session.delete(user)
    db_session.commit()

    # Clear cached ORM objects and query the database again.
    db_session.expire_all()

    remaining = db_session.execute(
        select(UserResourceInteraction).where(
            UserResourceInteraction.id == interaction_id
        )
    ).scalar_one_or_none()

    assert remaining is None
    assert db_session.get(User, user_id) is None

def test_resource_deletion_cascades_interactions(db_session):
    user = create_user(db_session)
    resource = create_resource(db_session)

    interaction = create_interaction(
        db_session,
        user,
        resource,
    )

    db_session.commit()

    interaction_id = interaction.id
    resource_id = resource.id

    db_session.delete(resource)
    db_session.commit()

    # Clear cached ORM objects and query the database again.
    db_session.expire_all()

    remaining = db_session.execute(
        select(UserResourceInteraction).where(
            UserResourceInteraction.id == interaction_id
        )
    ).scalar_one_or_none()

    assert remaining is None
    assert db_session.get(StudyResource, resource_id) is None