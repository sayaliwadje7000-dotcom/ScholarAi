from types import SimpleNamespace
from uuid import uuid4

import numpy as np
import pytest

from app.services.recommendations.ml.inference import (
    InferenceInputError,
    ModelCompatibilityError,
    ModelNotAvailableError,
    PredictionError,
    RecommendationInferenceConfig,
    RecommendationMLService,
)


class FakeFeatureExtractor:
    def extract(
        self,
        user_id,
        resource_ids,
        prediction_at=None,
    ):
        return [
            SimpleNamespace(
                resource_id=resource_id,
                to_model_features=lambda rid=resource_id: {
                    "resource_id": str(rid),
                    "difficulty": "beginner",
                },
            )
            for resource_id in resource_ids
        ]


class FakeTransformer:
    def transform(self, records):
        return SimpleNamespace(
            matrix=np.asarray(
                [[1.0] for _ in records],
                dtype=np.float64,
            )
        )


class FakeModel:
    def __init__(self, probabilities=None):
        self.probabilities = probabilities

    def predict_relevance_probability(self, matrix):
        if self.probabilities is None:
            return np.full(
                len(matrix),
                0.75,
                dtype=np.float64,
            )

        return np.asarray(
            self.probabilities,
            dtype=np.float64,
        )


def make_service(
    model=None,
    transformer=None,
    extractor=None,
    config=None,
    model_run_id="run-001",
):
    return RecommendationMLService(
        model=model or FakeModel(),
        feature_transformer=transformer or FakeTransformer(),
        feature_extractor=extractor or FakeFeatureExtractor(),
        model_run_id=model_run_id,
        config=config,
    )


def test_service_is_available():
    service = make_service()

    assert service.is_available() is True


def test_service_rejects_missing_model():
    with pytest.raises(ModelNotAvailableError):
        RecommendationMLService(
            model=None,
            feature_transformer=FakeTransformer(),
            feature_extractor=FakeFeatureExtractor(),
            model_run_id="run-001",
        )


def test_service_rejects_missing_transformer():
    with pytest.raises(ModelNotAvailableError):
        RecommendationMLService(
            model=FakeModel(),
            feature_transformer=None,
            feature_extractor=FakeFeatureExtractor(),
            model_run_id="run-001",
        )


def test_service_rejects_missing_model_run_id():
    with pytest.raises(ModelCompatibilityError):
        RecommendationMLService(
            model=FakeModel(),
            feature_transformer=FakeTransformer(),
            feature_extractor=FakeFeatureExtractor(),
            model_run_id=None,
        )


def test_successful_prediction():
    user_id = uuid4()
    resource_ids = [uuid4(), uuid4()]

    service = make_service()

    result = service.predict(
        user_id=user_id,
        resource_ids=resource_ids,
    )

    assert result.user_id == user_id
    assert len(result.predictions) == 2

    assert result.predictions[0].resource_id == resource_ids[0]
    assert result.predictions[1].resource_id == resource_ids[1]

    assert all(
        prediction.relevance_probability == 0.75
        for prediction in result.predictions
    )


def test_prediction_threshold_is_applied():
    user_id = uuid4()
    resource_ids = [uuid4(), uuid4()]

    service = make_service(
        model=FakeModel([0.8, 0.3]),
        config=RecommendationInferenceConfig(
            relevance_threshold=0.5
        ),
    )

    result = service.predict(
        user_id=user_id,
        resource_ids=resource_ids,
    )

    assert result.predictions[0].is_relevant is True
    assert result.predictions[1].is_relevant is False


def test_rejects_non_uuid_user_id():
    service = make_service()

    with pytest.raises(InferenceInputError):
        service.predict(
            user_id="invalid",
            resource_ids=[uuid4()],
        )


def test_rejects_non_uuid_resource_id():
    service = make_service()

    with pytest.raises(InferenceInputError):
        service.predict(
            user_id=uuid4(),
            resource_ids=["invalid"],
        )


def test_rejects_duplicate_resource_ids():
    service = make_service()
    resource_id = uuid4()

    with pytest.raises(InferenceInputError):
        service.predict(
            user_id=uuid4(),
            resource_ids=[
                resource_id,
                resource_id,
            ],
        )


def test_rejects_too_many_candidates():
    service = make_service(
        config=RecommendationInferenceConfig(
            maximum_candidates=1
        )
    )

    with pytest.raises(InferenceInputError):
        service.predict(
            user_id=uuid4(),
            resource_ids=[
                uuid4(),
                uuid4(),
            ],
        )


def test_rejects_prediction_count_mismatch():
    service = make_service(
        model=FakeModel([0.8])
    )

    with pytest.raises(PredictionError):
        service.predict(
            user_id=uuid4(),
            resource_ids=[
                uuid4(),
                uuid4(),
            ],
        )


def test_rejects_non_finite_probabilities():
    service = make_service(
        model=FakeModel([float("nan")])
    )

    with pytest.raises(PredictionError):
        service.predict(
            user_id=uuid4(),
            resource_ids=[uuid4()],
        )


def test_rejects_probabilities_outside_range():
    service = make_service(
        model=FakeModel([1.5])
    )

    with pytest.raises(PredictionError):
        service.predict(
            user_id=uuid4(),
            resource_ids=[uuid4()],
        )


def test_transformer_failure_is_reported():
    class BrokenTransformer:
        def transform(self, records):
            raise RuntimeError("transform failure")

    service = make_service(
        transformer=BrokenTransformer()
    )

    with pytest.raises(ModelCompatibilityError):
        service.predict(
            user_id=uuid4(),
            resource_ids=[uuid4()],
        )


def test_model_failure_is_reported():
    class BrokenModel:
        def predict_relevance_probability(self, matrix):
            raise RuntimeError("prediction failure")

    service = make_service(
        model=BrokenModel()
    )

    with pytest.raises(PredictionError):
        service.predict(
            user_id=uuid4(),
            resource_ids=[uuid4()],
        )


def test_empty_candidates_are_rejected_by_default():
    service = make_service()

    with pytest.raises(InferenceInputError):
        service.predict(
            user_id=uuid4(),
            resource_ids=[],
        )


def test_empty_candidates_can_be_allowed():
    service = make_service(
        config=RecommendationInferenceConfig(
            allow_empty_predictions=True
        )
    )

    result = service.predict(
        user_id=uuid4(),
        resource_ids=[],
    )

    assert result.predictions == ()