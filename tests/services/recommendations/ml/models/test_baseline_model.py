import numpy as np

import pytest

from scipy.sparse import csr_matrix

from app.services.recommendations.ml.models.model_config import (
    BaselineModelConfig,
)

from app.services.recommendations.ml.models.baseline_model import (
    BaselineModelNotFittedError,
    InvalidTrainingDataError,
    RecommendationBaselineModel,
    RecommendationDummyBaseline,
)


@pytest.fixture
def training_data():

    X = np.array(
        [
            [1.0, 0.0, 4.5, 3.0],
            [1.0, 0.0, 4.0, 2.0],
            [0.0, 1.0, 2.0, 0.0],
            [0.0, 1.0, 1.5, 0.0],
            [1.0, 0.0, 4.8, 5.0],
            [0.0, 1.0, 2.5, 1.0],
            [1.0, 0.0, 4.2, 4.0],
            [0.0, 1.0, 1.0, 0.0],
        ]
    )

    y = np.array(
        [1, 1, 0, 0, 1, 0, 1, 0]
    )

    feature_names = (
        "resource_type_video",
        "resource_type_article",
        "quality_score",
        "historical_save_count",
    )

    return X, y, feature_names


def test_model_trains_successfully(training_data):

    X, y, names = training_data

    model = RecommendationBaselineModel()

    summary = model.fit(
        X,
        y,
        feature_names=names,
    )

    assert model.is_fitted is True

    assert summary.training_samples == 8

    assert summary.feature_count == 4

    assert summary.classes == (0, 1)

    assert summary.model_name == (
        "scholarai_logistic_regression_baseline"
    )


def test_model_predicts_binary_labels(training_data):

    X, y, _ = training_data

    model = RecommendationBaselineModel()

    model.fit(X, y)

    predictions = model.predict(X)

    assert predictions.shape == (8,)

    assert set(predictions).issubset({0, 1})


def test_model_returns_class_probabilities(training_data):

    X, y, _ = training_data

    model = RecommendationBaselineModel()

    model.fit(X, y)

    probabilities = model.predict_proba(X)

    assert probabilities.shape == (8, 2)

    assert np.all(probabilities >= 0)

    assert np.all(probabilities <= 1)

    assert np.allclose(
        probabilities.sum(axis=1),
        1.0,
    )


def test_relevance_probability_is_returned(training_data):

    X, y, _ = training_data

    model = RecommendationBaselineModel()

    model.fit(X, y)

    probabilities = model.predict_relevance_probability(X)

    assert probabilities.shape == (8,)

    assert np.all(probabilities >= 0)

    assert np.all(probabilities <= 1)


def test_model_supports_sparse_matrices(training_data):

    X, y, names = training_data

    sparse_X = csr_matrix(X)

    model = RecommendationBaselineModel()

    model.fit(
        sparse_X,
        y,
        feature_names=names,
    )

    predictions = model.predict(sparse_X)

    assert predictions.shape == (8,)


def test_prediction_before_training_is_rejected():

    model = RecommendationBaselineModel()

    with pytest.raises(BaselineModelNotFittedError):

        model.predict(
            np.array([[1.0, 2.0]])
        )


def test_model_rejects_single_class_training_data():

    model = RecommendationBaselineModel()

    X = np.array(
        [
            [1.0, 2.0],
            [2.0, 3.0],
            [3.0, 4.0],
        ]
    )

    y = np.array([1, 1, 1])

    with pytest.raises(InvalidTrainingDataError):

        model.fit(X, y)


def test_model_rejects_invalid_labels():

    model = RecommendationBaselineModel()

    X = np.array(
        [
            [1.0],
            [2.0],
        ]
    )

    y = np.array([0, 2])

    with pytest.raises(InvalidTrainingDataError):

        model.fit(X, y)


def test_model_rejects_mismatched_samples():

    model = RecommendationBaselineModel()

    X = np.array(
        [
            [1.0],
            [2.0],
        ]
    )

    y = np.array([0])

    with pytest.raises(InvalidTrainingDataError):

        model.fit(X, y)


def test_model_rejects_invalid_feature_names(training_data):

    X, y, _ = training_data

    model = RecommendationBaselineModel()

    with pytest.raises(InvalidTrainingDataError):

        model.fit(
            X,
            y,
            feature_names=("only_one",),
        )


def test_model_rejects_wrong_prediction_dimensions(training_data):

    X, y, _ = training_data

    model = RecommendationBaselineModel()

    model.fit(X, y)

    with pytest.raises(InvalidTrainingDataError):

        model.predict(
            np.array([[1.0, 2.0]])
        )


def test_feature_coefficients_are_available(training_data):

    X, y, names = training_data

    model = RecommendationBaselineModel()

    model.fit(
        X,
        y,
        feature_names=names,
    )

    coefficients = model.get_feature_coefficients(
        top_n=3
    )

    assert len(coefficients) == 3

    assert all(
        coefficient.feature_name in names
        for coefficient in coefficients
    )


def test_model_configuration_is_validated():

    with pytest.raises(ValueError):

        BaselineModelConfig(
            regularization_strength=-1
        )

    with pytest.raises(ValueError):

        BaselineModelConfig(
            max_iterations=0
        )


def test_sample_weights_are_supported(training_data):

    X, y, _ = training_data

    weights = np.ones(len(y))

    model = RecommendationBaselineModel()

    model.fit(
        X,
        y,
        sample_weight=weights,
    )

    assert model.is_fitted


def test_invalid_sample_weights_are_rejected(training_data):

    X, y, _ = training_data

    weights = np.ones(len(y))

    weights[0] = -1

    model = RecommendationBaselineModel()

    with pytest.raises(InvalidTrainingDataError):

        model.fit(
            X,
            y,
            sample_weight=weights,
        )


def test_dummy_baseline_trains(training_data):

    X, y, _ = training_data

    model = RecommendationDummyBaseline()

    model.fit(X, y)

    predictions = model.predict(X)

    assert predictions.shape == (8,)


def test_dummy_baseline_returns_probabilities(training_data):

    X, y, _ = training_data

    model = RecommendationDummyBaseline()

    model.fit(X, y)

    probabilities = model.predict_proba(X)

    assert probabilities.shape == (8, 2)

    assert np.allclose(
        probabilities.sum(axis=1),
        1.0,
    )


def test_dummy_baseline_requires_training():

    model = RecommendationDummyBaseline()

    with pytest.raises(BaselineModelNotFittedError):

        model.predict(
            np.array([[1.0]])
        )