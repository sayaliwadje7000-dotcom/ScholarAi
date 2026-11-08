from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.services.recommendations.ml.dataset_schema import (
    DATASET_SCHEMA_VERSION,
    DatasetLabel,
    LabelSource,
    RecommendationTrainingExample,
)


def make_example(**overrides):

    values = {
        "user_id": uuid4(),
        "resource_id": uuid4(),
        "label": DatasetLabel.RELEVANT,
        "label_source": LabelSource.INTERACTION,
        "source_event": "save",
        "observed_at": datetime.now(timezone.utc),
    }

    values.update(overrides)

    return RecommendationTrainingExample(**values)


def test_schema_version_is_attached():

    assert make_example().schema_version == DATASET_SCHEMA_VERSION


def test_sample_key_groups_user_and_resource():

    example = make_example()

    assert example.sample_key == (
        example.user_id,
        example.resource_id,
    )


def test_model_record_excludes_grouping_identifiers():

    example = make_example()

    record = example.to_model_record()

    assert "user_id" not in record
    assert "resource_id" not in record
    assert record["label"] == 1


def test_audit_record_retains_grouping_keys_as_strings():

    example = make_example()

    record = example.to_audit_record()

    assert record["user_id"] == str(example.user_id)
    assert record["resource_id"] == str(example.resource_id)


def test_naive_timestamp_is_rejected():

    with pytest.raises(ValueError, match="timezone-aware"):

        make_example(
            observed_at=datetime(2026, 1, 1)
        )


def test_invalid_confidence_is_rejected():

    with pytest.raises(ValueError, match="confidence"):

        make_example(confidence=1.1)


def test_unknown_schema_version_is_rejected():

    with pytest.raises(
        ValueError,
        match="unsupported dataset schema",
    ):

        make_example(schema_version="2.0")