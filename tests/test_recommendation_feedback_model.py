import uuid

import pytest
from sqlalchemy import CheckConstraint, UniqueConstraint

from app.models.recommendation_feedback import RecommendationFeedback


def create_feedback(**overrides):
    values = {
        "recommendation_id": uuid.uuid4(),
        "feedback_type": "helpful",
        "comment": "This recommendation was useful.",
    }

    values.update(overrides)

    return RecommendationFeedback(**values)


def test_feedback_model_creation():
    feedback = create_feedback()

    assert isinstance(feedback, RecommendationFeedback)
    assert feedback.id is not None
    assert feedback.feedback_type == "helpful"


def test_feedback_has_unique_id():
    first = create_feedback()
    second = create_feedback()

    assert first.id != second.id


@pytest.mark.parametrize(
    "feedback_type",
    [
        "helpful",
        "not_helpful",
        "irrelevant",
    ],
)
def test_supported_feedback_types(feedback_type):
    feedback = create_feedback(
        feedback_type=feedback_type,
    )

    assert feedback.feedback_type == feedback_type


def test_feedback_comment_is_optional():
    feedback = create_feedback(comment=None)

    assert feedback.comment is None


def test_feedback_comment_is_stored():
    feedback = create_feedback(
        comment="Good recommendation.",
    )

    assert feedback.comment == "Good recommendation."


def test_feedback_table_name():
    assert RecommendationFeedback.__tablename__ == (
        "recommendation_feedback"
    )


def test_feedback_has_check_constraint():
    constraints = {
        constraint.name
        for constraint in RecommendationFeedback.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "ck_recommendation_feedback_valid_type" in constraints


def test_feedback_has_unique_constraint():
    constraints = {
        constraint.name
        for constraint in RecommendationFeedback.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert (
        "uq_recommendation_feedback_recommendation_id"
        in constraints
    )


def test_feedback_has_expected_indexes():
    indexes = {
        index.name
        for index in RecommendationFeedback.__table__.indexes
    }

    expected = {
        "ix_recommendation_feedback_recommendation_id",
        "ix_recommendation_feedback_feedback_type",
        "ix_recommendation_feedback_created_at",
    }

    assert expected.issubset(indexes)


def test_feedback_repr():
    feedback = create_feedback()

    assert "RecommendationFeedback" in repr(feedback)