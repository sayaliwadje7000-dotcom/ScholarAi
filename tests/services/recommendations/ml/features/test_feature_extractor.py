from datetime import datetime, timedelta, timezone
from uuid import uuid4
from types import SimpleNamespace

import pytest

from app.models.study_resource import StudyResource
from app.models.resource_category import ResourceCategory

from app.services.recommendations.ml.features.feature_extractor import (
    RecommendationFeatureExtractor,
    RecommendationFeatureExtractionError,
)


NOW = datetime(
    2026,
    11,
    7,
    12,
    0,
    tzinfo=timezone.utc,
)


def make_resource():

    resource = StudyResource(
        title="Introduction to Machine Learning",
        description="Machine learning fundamentals",
        resource_type="video",
        url="https://example.com/ml",
        provider="youtube",
        subject="Computer Science",
        language="English",
        difficulty_level="beginner",
        estimated_duration_minutes=30,
        quality_score=4.5,
        resource_metadata={
            "topics": ["Supervised Learning"],
            "keywords": ["Classification"],
            "learning_objectives": ["Understand models"],
            "prerequisites": ["Basic mathematics"],
        },
        is_active=True,
    )

    resource.published_at = NOW - timedelta(days=30)

    resource.categories = [
        ResourceCategory(
            name="Machine Learning",
            slug="machine-learning",
            is_active=True,
        ),
        ResourceCategory(
            name="Inactive Category",
            slug="inactive-category",
            is_active=False,
        ),
    ]

    return resource


def make_interaction(
    user_id,
    resource_id,
    interaction_type,
    occurred_at,
    rating=None,
):

    return SimpleNamespace(
        user_id=user_id,
        resource_id=resource_id,
        interaction_type=interaction_type,
        occurred_at=occurred_at,
        rating=rating,
    )


def test_extracts_resource_and_user_features():

    user_id = uuid4()

    resource = make_resource()

    preferences = SimpleNamespace(
        preferred_language="English",
        education_level="Undergraduate",
        preferred_subjects=["Computer Science"],
        learning_goals=["Exam Preparation"],
    )

    extractor = RecommendationFeatureExtractor()

    result = extractor.extract(
        user_id=user_id,
        resource=resource,
        preferences=preferences,
        interactions=[],
        prediction_at=NOW,
    )

    assert result.resource_type == "video"

    assert result.preferred_language == "english"

    assert result.preferred_subjects == (
        "computer science",
    )

    assert result.categories == (
        "machine-learning",
    )

    assert result.quality_score == 4.5

    assert result.resource_age_days == 30.0


def test_extracts_only_historical_interactions():

    user_id = uuid4()

    resource = make_resource()

    target_id = resource.id

    other_resource_id = uuid4()

    interactions = [
        make_interaction(
            user_id,
            other_resource_id,
            "view",
            NOW - timedelta(days=3),
        ),
        make_interaction(
            user_id,
            other_resource_id,
            "click",
            NOW - timedelta(days=2),
        ),
        make_interaction(
            user_id,
            other_resource_id,
            "save",
            NOW - timedelta(days=1),
        ),
        make_interaction(
            user_id,
            other_resource_id,
            "complete",
            NOW - timedelta(hours=1),
        ),
        make_interaction(
            user_id,
            other_resource_id,
            "rate",
            NOW - timedelta(minutes=30),
            rating=5,
        ),
        # Future interaction must not be used.
        make_interaction(
            user_id,
            other_resource_id,
            "click",
            NOW + timedelta(days=1),
        ),
        # Target-resource interaction must be excluded.
        make_interaction(
            user_id,
            target_id,
            "save",
            NOW - timedelta(days=1),
        ),
        # Other users must be excluded.
        make_interaction(
            uuid4(),
            other_resource_id,
            "click",
            NOW - timedelta(days=1),
        ),
    ]

    result = RecommendationFeatureExtractor().extract(
        user_id=user_id,
        resource=resource,
        preferences=None,
        interactions=interactions,
        prediction_at=NOW,
    )

    assert result.historical_view_count == 1
    assert result.historical_click_count == 1
    assert result.historical_save_count == 1
    assert result.historical_completion_count == 1
    assert result.historical_rating_count == 1
    assert result.historical_average_rating == 5.0


def test_missing_preferences_are_supported():

    result = RecommendationFeatureExtractor().extract(
        user_id=uuid4(),
        resource=make_resource(),
        preferences=None,
        interactions=[],
        prediction_at=NOW,
    )

    assert result.preferred_language is None
    assert result.preferred_subjects == ()


def test_ready_resource_embedding_is_extracted():

    embedding = SimpleNamespace(
        status="ready",
        embedding=[0.1, 0.2, 0.3],
    )

    result = RecommendationFeatureExtractor().extract(
        user_id=uuid4(),
        resource=make_resource(),
        preferences=None,
        interactions=[],
        prediction_at=NOW,
        resource_embedding=embedding,
    )

    assert result.resource_embedding == (
        0.1,
        0.2,
        0.3,
    )


def test_failed_embedding_is_ignored():

    embedding = SimpleNamespace(
        status="failed",
        embedding=None,
    )

    result = RecommendationFeatureExtractor().extract(
        user_id=uuid4(),
        resource=make_resource(),
        preferences=None,
        interactions=[],
        prediction_at=NOW,
        resource_embedding=embedding,
    )

    assert result.resource_embedding is None


def test_naive_prediction_time_is_rejected():

    with pytest.raises(
        RecommendationFeatureExtractionError
    ):

        RecommendationFeatureExtractor().extract(
            user_id=uuid4(),
            resource=make_resource(),
            preferences=None,
            interactions=[],
            prediction_at=datetime(2026, 1, 1),
        )