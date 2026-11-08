from datetime import datetime, timezone
from uuid import uuid4

from app.models.study_resource import StudyResource

from app.services.recommendations.ml.features.feature_pipeline import (
    RecommendationFeaturePipeline,
)


NOW = datetime(
    2026,
    11,
    7,
    12,
    0,
    tzinfo=timezone.utc,
)


def make_candidate():

    resource = StudyResource(
        title="Python Programming",
        description="Learn Python fundamentals",
        resource_type="course",
        url="https://example.com/python",
        provider="openalex",
        subject="computer science",
        language="english",
        difficulty_level="beginner",
        estimated_duration_minutes=60,
        quality_score=4.5,
        resource_metadata={
            "topics": ["python"],
            "keywords": ["programming"],
        },
    )

    return {
        "user_id": uuid4(),
        "resource": resource,
        "preferences": None,
        "interactions": [],
        "prediction_at": NOW,
        "resource_embedding": None,
    }


def test_pipeline_fit_transform():

    pipeline = RecommendationFeaturePipeline()

    candidates = [
        make_candidate(),
        make_candidate(),
    ]

    result = pipeline.fit_transform(candidates)

    assert len(result.rows) == 2

    assert result.transformation.row_count == 2

    assert result.transformation.feature_count > 0


def test_pipeline_transform_after_fitting():

    pipeline = RecommendationFeaturePipeline()

    pipeline.fit_transform(
        [
            make_candidate(),
            make_candidate(),
        ]
    )

    result = pipeline.transform(
        [
            make_candidate(),
        ]
    )

    assert len(result.rows) == 1

    assert result.transformation.row_count == 1


def test_pipeline_rejects_empty_candidates():

    pipeline = RecommendationFeaturePipeline()

    try:

        pipeline.fit_transform([])

        assert False, "Expected ValueError"

    except ValueError:
        pass