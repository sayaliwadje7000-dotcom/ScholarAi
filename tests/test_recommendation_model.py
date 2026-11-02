import uuid

import pytest
from sqlalchemy import CheckConstraint

from app.models.recommendation import Recommendation


def create_recommendation(**overrides):
    values = {
        "user_id": uuid.uuid4(),
        "resource_id": uuid.uuid4(),
        "recommendation_type": "personalized",
        "score": 0.85,
        "rank_position": 1,
        "reason": "Recommended based on previous learning activity.",
    }

    values.update(overrides)

    return Recommendation(**values)


def test_recommendation_model_creation():
    recommendation = create_recommendation()

    assert isinstance(recommendation, Recommendation)
    assert recommendation.id is not None
    assert recommendation.recommendation_type == "personalized"
    assert recommendation.score == 0.85
    assert recommendation.rank_position == 1


def test_recommendation_default_status():
    recommendation = create_recommendation()

    assert recommendation.status == "generated"


def test_recommendation_default_algorithm_version():
    recommendation = create_recommendation()

    assert recommendation.algorithm_version == "v1"


def test_recommendation_default_metadata():
    recommendation = create_recommendation()

    assert recommendation.recommendation_metadata == {}


def test_recommendation_unique_ids():
    first = create_recommendation()
    second = create_recommendation()

    assert first.id != second.id


@pytest.mark.parametrize(
    "recommendation_type",
    [
        "personalized",
        "trending",
        "related",
        "popular",
        "continue_learning",
    ],
)
def test_supported_recommendation_types(recommendation_type):
    recommendation = create_recommendation(
        recommendation_type=recommendation_type
    )

    assert recommendation.recommendation_type == recommendation_type


@pytest.mark.parametrize(
    "status",
    [
        "generated",
        "presented",
        "clicked",
        "dismissed",
        "expired",
    ],
)
def test_supported_status_values(status):
    recommendation = create_recommendation(status=status)

    assert recommendation.status == status


def test_recommendation_metadata_accepts_dictionary():
    recommendation = create_recommendation(
        recommendation_metadata={
            "subject": "Data Structures",
            "source": "learning_history",
        }
    )

    assert recommendation.recommendation_metadata["subject"] == "Data Structures"


def test_recommendation_repr():
    recommendation = create_recommendation()

    assert "Recommendation" in repr(recommendation)


def test_recommendation_table_name():
    assert Recommendation.__tablename__ == "recommendations"


def test_recommendation_has_expected_constraints():
    constraints = {
        constraint.name
        for constraint in Recommendation.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    expected = {
        "ck_recommendations_valid_type",
        "ck_recommendations_valid_score",
        "ck_recommendations_valid_rank",
        "ck_recommendations_reason_nonempty",
        "ck_recommendations_valid_status",
        "ck_recommendations_algorithm_version_nonempty",
        "ck_recommendations_metadata_object",
        "ck_recommendations_valid_expiration",
    }

    assert expected.issubset(constraints)


def test_recommendation_has_expected_indexes():
    indexes = {
        index.name
        for index in Recommendation.__table__.indexes
    }

    expected = {
        "ix_recommendations_user_id",
        "ix_recommendations_resource_id",
        "ix_recommendations_status",
        "ix_recommendations_score",
        "ix_recommendations_generated_at",
        "ix_recommendations_user_rank",
        "ix_recommendations_user_status",
    }

    assert expected.issubset(indexes)