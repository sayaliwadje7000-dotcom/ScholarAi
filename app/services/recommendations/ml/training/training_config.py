"""Configuration for ScholarAI recommendation model training."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TrainingConfig:
    """Configuration for a recommendation training run."""

    validation_size: float = 0.20

    random_state: int = 42

    max_split_attempts: int = 200

    min_training_samples: int = 10

    min_validation_samples: int = 4

    group_by_user: bool = True

    def __post_init__(self) -> None:

        if not 0 < self.validation_size < 1:
            raise ValueError(
                "validation_size must be between 0 and 1"
            )

        if self.max_split_attempts < 1:
            raise ValueError(
                "max_split_attempts must be positive"
            )

        if self.min_training_samples < 4:
            raise ValueError(
                "min_training_samples must be at least 4"
            )

        if self.min_validation_samples < 2:
            raise ValueError(
                "min_validation_samples must be at least 2"
            )

        if not isinstance(self.random_state, int):
            raise TypeError(
                "random_state must be an integer"
            )

        if not isinstance(self.group_by_user, bool):
            raise TypeError(
                "group_by_user must be boolean"
            )

        if not self.group_by_user:
            raise ValueError(
                "User-level grouping is required to prevent "
                "the same user's examples appearing in both "
                "training and validation partitions."
            )