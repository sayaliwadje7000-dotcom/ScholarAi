import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database.session import SessionLocal
from app.models.user import User
from app.models.study_resource import StudyResource
from app.models.recommendation import Recommendation


@pytest.fixture
def db_session():
    session = SessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


def create_user(session):
    user = User(
        full_name="Recommendation Test User",
        email=f"recommendation_{uuid.uuid4().hex}@example.com",
    )

    session.add(user)
    session.flush()

    return user


def create_resource(session):
    resource = StudyResource(
        title="Recommendation Test Resource",
        description="Resource created for recommendation persistence testing.",
        resource_type="article",
        url=f"https://example.com/{uuid.uuid4().hex}",
        provider="Test Provider",
        subject="Computer Science",
        language="English",
        difficulty_level="beginner",
        estimated_duration_minutes=20,
        quality_score=0.90,
        metadata={"source": "test"},
        is_active=True,
    )

    session.add(resource)
    session.flush()

    return resource


def create_recommendation(session, user, resource, **overrides):
    values = {
        "user_id": user.id,
        "resource_id": resource.id,
        "recommendation_type": "personalized",
        "score": 0.85,
        "rank_position": 1,
        "reason": "Recommended based on learning history.",
    }

    values.update(overrides)

    recommendation = Recommendation(**values)

    session.add(recommendation)
    session.flush()

    return recommendation


def test_recommendation_persists_successfully(db_session):
    user = create_user(db_session)
    resource = create_resource(db_session)

    recommendation = create_recommendation(
        db_session,
        user,
        resource,
    )

    recommendation_id = recommendation.id
    user_id = user.id
    resource_id = resource.id

    db_session.commit()
    db_session.expire_all()

    saved = db_session.get(Recommendation, recommendation_id)

    assert saved is not None
    assert saved.user_id == user_id
    assert saved.resource_id == resource_id
    assert float(saved.score) == pytest.approx(0.85)


def test_recommendation_user_relationship(db_session):
    user = create_user(db_session)
    resource = create_resource(db_session)

    recommendation = create_recommendation(
        db_session,
        user,
        resource,
    )

    user_id = user.id

    db_session.commit()
    db_session.refresh(recommendation)

    assert recommendation.user.id == user_id


def test_recommendation_resource_relationship(db_session):
    user = create_user(db_session)
    resource = create_resource(db_session)

    recommendation = create_recommendation(
        db_session,
        user,
        resource,
    )

    resource_id = resource.id

    db_session.commit()
    db_session.refresh(recommendation)

    assert recommendation.resource.id == resource_id


def test_recommendation_metadata_persists(db_session):
    user = create_user(db_session)
    resource = create_resource(db_session)

    recommendation = create_recommendation(
        db_session,
        user,
        resource,
        recommendation_metadata={
            "subject": "Data Structures",
            "reason_code": "previous_activity",
        },
    )

    recommendation_id = recommendation.id

    db_session.commit()
    db_session.expire_all()

    saved = db_session.get(Recommendation, recommendation_id)

    assert saved is not None
    assert saved.recommendation_metadata["subject"] == "Data Structures"
    assert saved.recommendation_metadata["reason_code"] == "previous_activity"


def test_recommendation_rejects_invalid_score(db_session):
    user = create_user(db_session)
    resource = create_resource(db_session)

    with pytest.raises(IntegrityError):
        create_recommendation(
            db_session,
            user,
            resource,
            score=1.5,
        )
        db_session.commit()

    db_session.rollback()


def test_recommendation_rejects_zero_rank(db_session):
    user = create_user(db_session)
    resource = create_resource(db_session)

    with pytest.raises(IntegrityError):
        create_recommendation(
            db_session,
            user,
            resource,
            rank_position=0,
        )
        db_session.commit()

    db_session.rollback()


def test_recommendation_rejects_invalid_type(db_session):
    user = create_user(db_session)
    resource = create_resource(db_session)

    with pytest.raises(IntegrityError):
        create_recommendation(
            db_session,
            user,
            resource,
            recommendation_type="invalid_type",
        )
        db_session.commit()

    db_session.rollback()


def test_recommendation_rejects_invalid_status(db_session):
    user = create_user(db_session)
    resource = create_resource(db_session)

    with pytest.raises(IntegrityError):
        create_recommendation(
            db_session,
            user,
            resource,
            status="invalid_status",
        )
        db_session.commit()

    db_session.rollback()


def test_recommendation_rejects_empty_reason(db_session):
    user = create_user(db_session)
    resource = create_resource(db_session)

    with pytest.raises(IntegrityError):
        create_recommendation(
            db_session,
            user,
            resource,
            reason="   ",
        )
        db_session.commit()

    db_session.rollback()


def test_recommendation_rejects_empty_algorithm_version(db_session):
    user = create_user(db_session)
    resource = create_resource(db_session)

    with pytest.raises(IntegrityError):
        create_recommendation(
            db_session,
            user,
            resource,
            algorithm_version="   ",
        )
        db_session.commit()

    db_session.rollback()


def test_recommendation_rejects_expiration_before_generation(db_session):
    user = create_user(db_session)
    resource = create_resource(db_session)

    with pytest.raises(IntegrityError):
        create_recommendation(
            db_session,
            user,
            resource,
            expires_at="2000-01-01T00:00:00+00:00",
        )
        db_session.commit()

    db_session.rollback()


def test_recommendation_allows_score_boundaries(db_session):
    user = create_user(db_session)
    resource = create_resource(db_session)

    first = create_recommendation(
        db_session,
        user,
        resource,
        score=0,
        rank_position=1,
    )

    second = create_recommendation(
        db_session,
        user,
        resource,
        score=1,
        rank_position=2,
    )

    db_session.commit()
    db_session.refresh(first)
    db_session.refresh(second)

    assert float(first.score) == pytest.approx(0.0)
    assert float(second.score) == pytest.approx(1.0)


def test_recommendation_can_be_queried_by_user(db_session):
    user = create_user(db_session)
    resource = create_resource(db_session)

    recommendation = create_recommendation(
        db_session,
        user,
        resource,
    )

    user_id = user.id
    recommendation_id = recommendation.id

    db_session.commit()

    results = db_session.scalars(
        select(Recommendation).where(
            Recommendation.user_id == user_id
        )
    ).all()

    assert recommendation_id in [item.id for item in results]