import pytest

from app.services.recommendations.ml.training.training_config import (
    TrainingConfig,
)


def test_default_configuration():

    config = TrainingConfig()

    assert config.validation_size == 0.20

    assert config.random_state == 42

    assert config.group_by_user is True


def test_validation_size_must_be_valid():

    with pytest.raises(ValueError):

        TrainingConfig(
            validation_size=1.0
        )


def test_split_attempts_must_be_positive():

    with pytest.raises(ValueError):

        TrainingConfig(
            max_split_attempts=0
        )


def test_user_grouping_cannot_be_disabled():

    with pytest.raises(ValueError):

        TrainingConfig(
            group_by_user=False
        )


def test_minimum_training_samples():

    with pytest.raises(ValueError):

        TrainingConfig(
            min_training_samples=2
        )