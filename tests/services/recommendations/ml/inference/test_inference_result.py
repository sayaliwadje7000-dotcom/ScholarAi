from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.services.recommendations.ml.inference import (
    RecommendationPrediction,
    RecommendationPredictionBatch,
)


def test_prediction_creation():
    resource_id = uuid4()

    prediction = RecommendationPrediction(
        resource_id=resource_id,
        relevance_probability=0.85,
        is_relevant=True,
        model_run_id="run-001",
    )

    assert prediction.resource_id == resource_id
    assert prediction.relevance_probability == 0.85
    assert prediction.is_relevant is True


def test_prediction_rejects_invalid_probability():
    with pytest.raises(ValueError):
        RecommendationPrediction(
            resource_id=uuid4(),
            relevance_probability=1.5,
            is_relevant=True,
            model_run_id="run-001",
        )


def test_batch_creation():
    user_id = uuid4()
    resource_id = uuid4()

    prediction = RecommendationPrediction(
        resource_id=resource_id,
        relevance_probability=0.9,
        is_relevant=True,
        model_run_id="run-001",
    )

    batch = RecommendationPredictionBatch.create(
        user_id=user_id,
        predictions=(prediction,),
        model_run_id="run-001",
        prediction_threshold=0.5,
    )

    assert batch.user_id == user_id
    assert len(batch.predictions) == 1
    assert batch.model_run_id == "run-001"
    assert batch.generated_at.tzinfo is not None


def test_batch_rejects_duplicate_resources():
    user_id = uuid4()
    resource_id = uuid4()

    prediction_1 = RecommendationPrediction(
        resource_id=resource_id,
        relevance_probability=0.8,
        is_relevant=True,
        model_run_id="run-001",
    )

    prediction_2 = RecommendationPrediction(
        resource_id=resource_id,
        relevance_probability=0.6,
        is_relevant=True,
        model_run_id="run-001",
    )

    with pytest.raises(ValueError):
        RecommendationPredictionBatch(
            user_id=user_id,
            predictions=(prediction_1, prediction_2),
            model_run_id="run-001",
            prediction_threshold=0.5,
            generated_at=datetime.now(timezone.utc),
        )