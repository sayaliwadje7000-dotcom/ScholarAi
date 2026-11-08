from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.services.recommendations.ml.features.feature_schema import (
    RecommendationFeatureRow,
)


def make_row(**overrides):

    values = {
        "user_id": uuid4(),
        "resource_id": uuid4(),
        "prediction_at": datetime.now(timezone.utc),

        "preferred_language": "english",
        "education_level": "undergraduate",
        "preferred_subjects": ("computer science",),
        "learning_goals": ("exam preparation",),

        "resource_type": "video",
        "subject": "machine learning",
        "language": "english",
        "difficulty_level": "beginner",
        "provider": "youtube",

        "categories": ("artificial-intelligence",),

        "title": "Introduction to Machine Learning",
        "description": "Machine learning introduction",

        "topics": ("supervised learning",),
        "keywords": ("classification",),
        "learning_objectives": ("understand models",),
        "prerequisites": ("basic mathematics",),

        "quality_score": 4.5,
        "estimated_duration_minutes": 30.0,
        "resource_age_days": 120.0,

        "historical_view_count": 5,
        "historical_click_count": 3,
        "historical_save_count": 2,
        "historical_completion_count": 1,
        "historical_rating_count": 1,
        "historical_average_rating": 4.0,
    }

    values.update(overrides)

    return RecommendationFeatureRow(**values)


def test_feature_row_creation():

    row = make_row()

    assert row.resource_type == "video"
    assert row.quality_score == 4.5


def test_grouping_key():

    row = make_row()

    assert row.grouping_key == (
        row.user_id,
        row.resource_id,
    )


def test_identifiers_are_not_model_features():

    row = make_row()

    features = row.to_model_features()

    assert "user_id" not in features
    assert "resource_id" not in features
    assert "prediction_at" not in features


def test_negative_history_count_rejected():

    with pytest.raises(ValueError):

        make_row(
            historical_click_count=-1
        )


def test_invalid_quality_score_rejected():

    with pytest.raises(ValueError):

        make_row(
            quality_score=8
        )


def test_naive_prediction_timestamp_rejected():

    with pytest.raises(ValueError):

        make_row(
            prediction_at=datetime(2026, 1, 1)
        )


def test_embedding_values_must_be_finite():

    with pytest.raises(ValueError):

        make_row(
            resource_embedding=(1.0, float("nan"))
        )