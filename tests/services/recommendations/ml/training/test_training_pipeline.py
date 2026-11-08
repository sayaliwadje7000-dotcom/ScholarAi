from datetime import datetime, timezone
from uuid import uuid4

import numpy as np
import pytest

from app.services.recommendations.ml.dataset_schema import (
    DatasetLabel,
    LabelSource,
    RecommendationTrainingExample,
)

from app.services.recommendations.ml.features.feature_schema import (
    RecommendationFeatureRow,
)

from app.services.recommendations.ml.training.training_config import (
    TrainingConfig,
)

from app.services.recommendations.ml.training.training_pipeline import (
    DatasetAlignmentError,
    DatasetSplitError,
    RecommendationTrainingPipeline,
)


NOW = datetime(
    2026,
    11,
    8,
    12,
    0,
    tzinfo=timezone.utc,
)


def create_pair(
    user_id,
    resource_id,
    label,
):
    row = RecommendationFeatureRow(
        user_id=user_id,
        resource_id=resource_id,
        prediction_at=NOW,

        preferred_language="english",
        education_level="undergraduate",
        preferred_subjects=("computer science",),
        learning_goals=("exam preparation",),

        resource_type=(
            "video" if label == 1 else "article"
        ),

        subject="computer science",
        language="english",

        difficulty_level=(
            "beginner" if label == 1 else "advanced"
        ),

        provider="test_provider",

        categories=("machine-learning",),

        title=(
            "Introduction to machine learning"
            if label == 1
            else "Advanced unrelated mathematics"
        ),

        description=(
            "Learn machine learning fundamentals"
            if label == 1
            else "Advanced mathematical concepts"
        ),

        topics=("machine learning",),

        keywords=("algorithms",),

        learning_objectives=("understand concepts",),

        prerequisites=("basic mathematics",),

        quality_score=(
            4.5 if label == 1 else 2.0
        ),

        estimated_duration_minutes=30.0,

        resource_age_days=20.0,

        historical_view_count=2,

        historical_click_count=1,

        historical_save_count=(
            2 if label == 1 else 0
        ),

        historical_completion_count=(
            1 if label == 1 else 0
        ),

        historical_rating_count=1,

        historical_average_rating=(
            5.0 if label == 1 else 2.0
        ),
    )

    example = RecommendationTrainingExample(
        user_id=user_id,
        resource_id=resource_id,

        label=(
            DatasetLabel.RELEVANT
            if label == 1
            else DatasetLabel.NOT_RELEVANT
        ),

        label_source=LabelSource.INTERACTION,

        source_event=(
            "save" if label == 1 else "rating_1"
        ),

        observed_at=NOW,

        confidence=1.0,
    )

    return row, example


def make_dataset(user_count=40):

    rows = []

    examples = []

    for index in range(user_count):

        user_id = uuid4()

        label = index % 2

        resource_id = uuid4()

        row, example = create_pair(
            user_id=user_id,
            resource_id=resource_id,
            label=label,
        )

        rows.append(row)

        examples.append(example)

    return rows, examples


@pytest.fixture
def dataset():

    return make_dataset()


def test_training_pipeline_trains_models(dataset):

    rows, examples = dataset

    pipeline = RecommendationTrainingPipeline()

    result = pipeline.train(
        rows,
        examples,
    )

    assert result.model.is_fitted

    assert result.dummy_baseline is not None

    assert result.training_summary.training_samples > 0

    assert result.validation_statistics.total_samples > 0

    assert result.evaluation_dataset is not None


def test_training_and_validation_users_are_disjoint(dataset):

    rows, examples = dataset

    result = RecommendationTrainingPipeline().train(
        rows,
        examples,
    )

    training_users = set(
        result.training_user_ids
    )

    validation_users = set(
        result.validation_user_ids
    )

    assert training_users.isdisjoint(validation_users)

    assert (
        training_users | validation_users
        == {row.user_id for row in rows}
    )


def test_training_and_validation_users_are_recorded(dataset):

    rows, examples = dataset

    result = RecommendationTrainingPipeline().train(
        rows,
        examples,
    )

    assert len(result.training_user_ids) > 0

    assert len(result.validation_user_ids) > 0

    assert len(result.training_user_ids) == len(
        set(result.training_user_ids)
    )

    assert len(result.validation_user_ids) == len(
        set(result.validation_user_ids)
    )


def test_training_class_distribution_contains_both_classes(dataset):

    rows, examples = dataset

    result = RecommendationTrainingPipeline().train(
        rows,
        examples,
    )

    assert set(
        result.training_class_distribution
    ) == {0, 1}

    assert set(
        result.validation_class_distribution
    ) == {0, 1}


def test_validation_matrix_matches_validation_labels(dataset):

    rows, examples = dataset

    result = RecommendationTrainingPipeline().train(
        rows,
        examples,
    )

    assert (
        result.evaluation_dataset.X.shape[0]
        == len(result.evaluation_dataset.y)
    )

    assert (
        result.evaluation_dataset.statistics.total_samples
        == len(result.evaluation_dataset.y)
    )


def test_training_statistics_are_consistent(dataset):

    rows, examples = dataset

    result = RecommendationTrainingPipeline().train(
        rows,
        examples,
    )

    training_stats = result.training_statistics

    validation_stats = result.validation_statistics

    assert (
        training_stats.total_samples
        == training_stats.relevant_samples
        + training_stats.not_relevant_samples
    )

    assert (
        validation_stats.total_samples
        == validation_stats.relevant_samples
        + validation_stats.not_relevant_samples
    )


def test_training_pipeline_rejects_duplicate_feature_rows(dataset):

    rows, examples = dataset

    rows.append(rows[0])

    with pytest.raises(DatasetAlignmentError):

        RecommendationTrainingPipeline().train(
            rows,
            examples,
        )


def test_training_pipeline_rejects_duplicate_labels(dataset):

    rows, examples = dataset

    examples.append(examples[0])

    with pytest.raises(DatasetAlignmentError):

        RecommendationTrainingPipeline().train(
            rows,
            examples,
        )


def test_training_pipeline_rejects_missing_feature_rows(dataset):

    rows, examples = dataset

    rows.pop()

    with pytest.raises(DatasetAlignmentError):

        RecommendationTrainingPipeline().train(
            rows,
            examples,
        )


def test_training_pipeline_rejects_missing_labels(dataset):

    rows, examples = dataset

    examples.pop()

    with pytest.raises(DatasetAlignmentError):

        RecommendationTrainingPipeline().train(
            rows,
            examples,
        )


def test_training_pipeline_rejects_empty_dataset():

    with pytest.raises(DatasetAlignmentError):

        RecommendationTrainingPipeline().train(
            [],
            [],
        )


def test_training_pipeline_rejects_insufficient_users():

    rows, examples = make_dataset(user_count=3)

    with pytest.raises(DatasetSplitError):

        RecommendationTrainingPipeline().train(
            rows,
            examples,
        )


def test_training_pipeline_uses_confidence_weights():

    rows, examples = make_dataset()

    examples = [
        RecommendationTrainingExample(
            user_id=example.user_id,
            resource_id=example.resource_id,
            label=example.label,
            label_source=example.label_source,
            source_event=example.source_event,
            observed_at=example.observed_at,
            confidence=0.5,
        )
        for example in examples
    ]

    result = RecommendationTrainingPipeline().train(
        rows,
        examples,
    )

    assert result.model.is_fitted


def test_training_pipeline_is_reproducible(dataset):

    rows, examples = dataset

    config = TrainingConfig(
        random_state=42
    )

    first = RecommendationTrainingPipeline(
        config=config
    ).train(
        rows,
        examples,
    )

    second = RecommendationTrainingPipeline(
        config=config
    ).train(
        rows,
        examples,
    )

    assert (
        first.training_class_distribution
        == second.training_class_distribution
    )

    assert (
        first.validation_class_distribution
        == second.validation_class_distribution
    )

    assert (
        first.training_user_ids
        == second.training_user_ids
    )

    assert (
        first.validation_user_ids
        == second.validation_user_ids
    )

    assert np.allclose(
        first.model.predict_proba(
            first.evaluation_dataset.X
        ),
        second.model.predict_proba(
            second.evaluation_dataset.X
        ),
    )


def test_training_pipeline_produces_unique_run_ids(dataset):

    rows, examples = dataset

    first = RecommendationTrainingPipeline().train(
        rows,
        examples,
    )

    second = RecommendationTrainingPipeline().train(
        rows,
        examples,
    )

    assert first.run_id != second.run_id


def test_training_pipeline_preserves_validation_labels(dataset):

    rows, examples = dataset

    result = RecommendationTrainingPipeline().train(
        rows,
        examples,
    )

    labels = result.evaluation_dataset.y

    assert set(np.unique(labels)) == {0, 1}

    assert labels.dtype == np.int64