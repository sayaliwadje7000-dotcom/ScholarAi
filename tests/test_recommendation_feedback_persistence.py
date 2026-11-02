import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database.session import SessionLocal
from app.models.user import User
from app.models.study_resource import StudyResource
from app.models.recommendation import Recommendation
from app.models.recommendation_feedback import RecommendationFeedback


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
        full_name="Feedback Test User",
        email=f"feedback_{uuid.uuid4().hex}@example.com",
    )

    session.add(user)
    session.flush()

    return user


def create_resource(session):
    resource = StudyResource(
        title="Feedback Test Resource",
        description="Resource created for feedback testing.",
        resource_type="article",
        url=f"https://example.com/feedback/{uuid.uuid4().hex}",
        provider="Test Provider",
        subject="Computer Science",
        language="English",
        difficulty_level="beginner",
        estimated_duration_minutes=20,
        quality_score=0.90,
        metadata={"source": "feedback_test"},
        is_active=True,
    )

    session.add(resource)
    session.flush()

    return resource


def create_recommendation(session, user, resource):
    recommendation = Recommendation(
        user_id=user.id,
        resource_id=resource.id,
        recommendation_type="personalized",
        score=0.85,
        rank_position=1,
        reason="Recommended based on learning history.",
    )

    session.add(recommendation)
    session.flush()

    return recommendation


def create_feedback(session, recommendation, **overrides):
    values = {
        "recommendation_id": recommendation.id,
        "feedback_type": "helpful",
        "comment": "This recommendation was useful.",
    }

    values.update(overrides)

    feedback = RecommendationFeedback(**values)

    session.add(feedback)
    session.flush()

    return feedback


def create_test_data(session):
    user = create_user(session)
    resource = create_resource(session)
    recommendation = create_recommendation(
        session,
        user,
        resource,
    )

    return user, resource, recommendation


def test_feedback_persists_successfully(db_session):
    _, _, recommendation = create_test_data(db_session)

    feedback = create_feedback(
        db_session,
        recommendation,
    )

    feedback_id = feedback.id
    recommendation_id = recommendation.id

    db_session.commit()
    db_session.expire_all()

    saved = db_session.get(
        RecommendationFeedback,
        feedback_id,
    )

    assert saved is not None
    assert saved.recommendation_id == recommendation_id
    assert saved.feedback_type == "helpful"


def test_feedback_recommendation_relationship(db_session):
    _, _, recommendation = create_test_data(db_session)

    feedback = create_feedback(
        db_session,
        recommendation,
    )

    recommendation_id = recommendation.id

    db_session.commit()
    db_session.refresh(feedback)

    assert feedback.recommendation.id == recommendation_id


def test_recommendation_feedback_entries_relationship(db_session):
    _, _, recommendation = create_test_data(db_session)

    feedback = create_feedback(
        db_session,
        recommendation,
    )

    feedback_id = feedback.id

    db_session.commit()
    db_session.refresh(recommendation)

    assert len(recommendation.feedback_entries) == 1
    assert recommendation.feedback_entries[0].id == feedback_id


@pytest.mark.parametrize(
    "feedback_type",
    [
        "helpful",
        "not_helpful",
        "irrelevant",
    ],
)
def test_feedback_accepts_supported_types(
    db_session,
    feedback_type,
):
    _, _, recommendation = create_test_data(db_session)

    feedback = create_feedback(
        db_session,
        recommendation,
        feedback_type=feedback_type,
    )

    db_session.commit()

    assert feedback.feedback_type == feedback_type


def test_feedback_rejects_invalid_type(db_session):
    _, _, recommendation = create_test_data(db_session)

    with pytest.raises(IntegrityError):
        create_feedback(
            db_session,
            recommendation,
            feedback_type="invalid",
        )

        db_session.commit()

    db_session.rollback()


def test_feedback_rejects_duplicate_recommendation_feedback(
    db_session,
):
    _, _, recommendation = create_test_data(db_session)

    create_feedback(
        db_session,
        recommendation,
    )

    db_session.commit()

    duplicate = RecommendationFeedback(
        recommendation_id=recommendation.id,
        feedback_type="not_helpful",
    )

    db_session.add(duplicate)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_feedback_comment_persists(db_session):
    _, _, recommendation = create_test_data(db_session)

    feedback = create_feedback(
        db_session,
        recommendation,
        comment="Excellent resource for revision.",
    )

    feedback_id = feedback.id

    db_session.commit()
    db_session.expire_all()

    saved = db_session.get(
        RecommendationFeedback,
        feedback_id,
    )

    assert saved.comment == "Excellent resource for revision."


def test_feedback_allows_null_comment(db_session):
    _, _, recommendation = create_test_data(db_session)

    feedback = create_feedback(
        db_session,
        recommendation,
        comment=None,
    )

    db_session.commit()

    assert feedback.comment is None


def test_feedback_can_be_queried_by_recommendation(db_session):
    _, _, recommendation = create_test_data(db_session)

    feedback = create_feedback(
        db_session,
        recommendation,
    )

    feedback_id = feedback.id
    recommendation_id = recommendation.id

    db_session.commit()

    results = db_session.scalars(
        select(RecommendationFeedback).where(
            RecommendationFeedback.recommendation_id
            == recommendation_id
        )
    ).all()

    assert feedback_id in [item.id for item in results]


def test_deleting_recommendation_deletes_feedback(db_session):
    _, _, recommendation = create_test_data(db_session)

    feedback = create_feedback(
        db_session,
        recommendation,
    )

    recommendation_id = recommendation.id
    feedback_id = feedback.id

    db_session.commit()

    db_session.execute(
        Recommendation.__table__.delete().where(
            Recommendation.id == recommendation_id
        )
    )

    db_session.commit()
    db_session.expire_all()

    saved = db_session.get(
        RecommendationFeedback,
        feedback_id,
    )

    assert saved is None