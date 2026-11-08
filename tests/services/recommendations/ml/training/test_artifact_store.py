from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.services.recommendations.ml.dataset_schema import (
    DatasetLabel,
    LabelSource,
    RecommendationTrainingExample,
)

from app.services.recommendations.ml.features.feature_schema import (
    RecommendationFeatureRow,
)

from app.services.recommendations.ml.training.training_pipeline import (
    RecommendationTrainingPipeline,
)

from app.services.recommendations.ml.training.artifact_store import (
    ModelArtifactError,
    ModelArtifactStore,
)


NOW = datetime(
    2026,
    11,
    8,
    12,
    0,
    tzinfo=timezone.utc,
)


def create_dataset():

    rows = []

    examples = []

    for index in range(40):

        user_id = uuid4()

        resource_id = uuid4()

        label = index % 2

        row = RecommendationFeatureRow(
            user_id=user_id,
            resource_id=resource_id,
            prediction_at=NOW,

            preferred_language="english",
            education_level="undergraduate",
            preferred_subjects=("computer science",),
            learning_goals=("learning",),

            resource_type=(
                "video" if label else "article"
            ),

            subject="computer science",
            language="english",
            difficulty_level="beginner",
            provider="test",

            categories=("machine-learning",),

            title=(
                "Machine learning fundamentals"
                if label
                else "Unrelated mathematics"
            ),

            description="Learning resource",

            topics=("machine learning",),
            keywords=("algorithms",),
            learning_objectives=("understand concepts",),
            prerequisites=("mathematics",),

            quality_score=4.0 if label else 2.0,
            estimated_duration_minutes=30.0,
            resource_age_days=20.0,

            historical_view_count=1,
            historical_click_count=1,
            historical_save_count=label,
            historical_completion_count=label,
            historical_rating_count=1,
            historical_average_rating=(
                5.0 if label else 2.0
            ),
        )

        example = RecommendationTrainingExample(
            user_id=user_id,
            resource_id=resource_id,
            label=(
                DatasetLabel.RELEVANT
                if label
                else DatasetLabel.NOT_RELEVANT
            ),
            label_source=LabelSource.INTERACTION,
            source_event="click",
            observed_at=NOW,
        )

        rows.append(row)

        examples.append(example)

    return rows, examples


@pytest.fixture
def training_result():

    rows, examples = create_dataset()

    return RecommendationTrainingPipeline().train(
        rows,
        examples,
    )


def test_artifact_is_saved_and_loaded(
    tmp_path,
    training_result,
):

    store = ModelArtifactStore()

    destination = (
        tmp_path / "scholarai_baseline.joblib"
    )

    saved_path = store.save(
        training_result,
        destination,
    )

    assert saved_path.exists()

    payload = store.load(saved_path)

    assert payload["model"].is_fitted

    assert payload["model_name"] == (
        "scholarai_logistic_regression_baseline"
    )

    assert payload["run_id"] == training_result.run_id


def test_artifact_rejects_wrong_extension(
    tmp_path,
    training_result,
):

    store = ModelArtifactStore()

    with pytest.raises(ModelArtifactError):

        store.save(
            training_result,
            tmp_path / "model.pkl",
        )


def test_artifact_rejects_missing_file(tmp_path):

    store = ModelArtifactStore()

    with pytest.raises(ModelArtifactError):

        store.load(
            tmp_path / "missing.joblib"
        )


def test_loaded_model_can_predict(
    tmp_path,
    training_result,
):

    store = ModelArtifactStore()

    destination = (
        tmp_path / "scholarai_baseline.joblib"
    )

    store.save(
        training_result,
        destination,
    )

    payload = store.load(destination)

    model = payload["model"]

    predictions = model.predict(
        training_result.evaluation_dataset.X
    )

    assert len(predictions) == (
        len(training_result.evaluation_dataset.y)
    )