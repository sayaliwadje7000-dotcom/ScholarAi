import pytest

from app.services.recommendations.ml.inference import (
    RecommendationInferenceConfig,
)


def test_default_configuration():
    config = RecommendationInferenceConfig()

    assert config.relevance_threshold == 0.5
    assert config.maximum_candidates == 500
    assert config.minimum_candidates == 1


@pytest.mark.parametrize(
    "threshold",
    [-0.1, 1.1],
)
def test_invalid_relevance_threshold(threshold):
    with pytest.raises(ValueError):
        RecommendationInferenceConfig(
            relevance_threshold=threshold
        )


def test_invalid_candidate_limit():
    with pytest.raises(ValueError):
        RecommendationInferenceConfig(
            maximum_candidates=0
        )


def test_minimum_candidates_cannot_exceed_maximum():
    with pytest.raises(ValueError):
        RecommendationInferenceConfig(
            minimum_candidates=10,
            maximum_candidates=5,
        )