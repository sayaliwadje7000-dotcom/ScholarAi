from pathlib import Path

import pytest

from app.services.recommendations.ml.experiments.experiment_config import (
    ExperimentTrackingConfig,
)


def test_default_experiment_configuration():

    config = ExperimentTrackingConfig()

    assert config.schema_version == "1.0"

    assert config.include_environment_metadata is True

    assert config.include_dataset_fingerprint is True

    assert config.allow_overwrite is False


def test_storage_directory_is_normalized(tmp_path):

    directory = tmp_path / "experiments"

    config = ExperimentTrackingConfig(
        storage_directory=str(directory)
    )

    assert isinstance(
        config.storage_directory,
        Path,
    )

    assert config.storage_directory == directory


def test_empty_schema_version_is_rejected():

    with pytest.raises(ValueError):

        ExperimentTrackingConfig(
            schema_version=" "
        )


def test_existing_file_cannot_be_used_as_storage_directory(
    tmp_path,
):

    file_path = tmp_path / "not_a_directory"

    file_path.write_text(
        "test",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):

        ExperimentTrackingConfig(
            storage_directory=file_path
        )