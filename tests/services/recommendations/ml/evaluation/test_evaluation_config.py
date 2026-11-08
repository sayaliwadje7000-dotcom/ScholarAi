import pytest

from app.services.recommendations.ml.evaluation.evaluation_config import (
    EvaluationConfig,
    EvaluationConfigurationError,
)


def test_default_evaluation_config():

    config = EvaluationConfig()

    assert config.classification_threshold == 0.50

    assert config.ranking_k_values == (3, 5, 10)


def test_custom_evaluation_config():

    config = EvaluationConfig(
        classification_threshold=0.65,
        ranking_k_values=(2, 4, 8),
    )

    assert config.classification_threshold == 0.65

    assert config.ranking_k_values == (2, 4, 8)


@pytest.mark.parametrize(
    "threshold",
    [
        0,
        1,
        -0.1,
        1.1,
    ],
)
def test_invalid_threshold(threshold):

    with pytest.raises(EvaluationConfigurationError):

        EvaluationConfig(
            classification_threshold=threshold,
        )


@pytest.mark.parametrize(
    "ranking_values",
    [
        (),
        (0,),
        (-1,),
        (3, 3),
        (3, 5, 3),
    ],
)
def test_invalid_ranking_values(ranking_values):

    with pytest.raises(EvaluationConfigurationError):

        EvaluationConfig(
            ranking_k_values=ranking_values,
        )


def test_invalid_class_labels():

    with pytest.raises(EvaluationConfigurationError):

        EvaluationConfig(
            positive_label=1,
            negative_label=1,
        )