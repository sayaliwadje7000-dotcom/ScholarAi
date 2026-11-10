import pytest

from app.scoring.configuration import ScoringConfiguration
from app.scoring.exceptions import ScoringConfigurationError


def test_weights_are_normalized():
    config = ScoringConfiguration(
        weights={
            "relevance": 2,
            "quality": 2,
        }
    )

    assert config.normalized_weights() == {
        "relevance": 0.5,
        "quality": 0.5,
    }


def test_empty_weights_are_rejected():
    with pytest.raises(ScoringConfigurationError):
        ScoringConfiguration(weights={})


def test_negative_weights_are_rejected():
    with pytest.raises(ScoringConfigurationError):
        ScoringConfiguration(
            weights={"relevance": -1}
        )


def test_zero_total_weights_are_rejected():
    with pytest.raises(ScoringConfigurationError):
        ScoringConfiguration(
            weights={
                "relevance": 0,
                "quality": 0,
            }
        )