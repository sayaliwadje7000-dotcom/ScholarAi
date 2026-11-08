"""Dataset privacy and separation validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
from uuid import UUID

from app.services.recommendations.ml.privacy.privacy_config import (
    PrivacyConfig,
)

from app.services.recommendations.ml.privacy.privacy_exceptions import (
    DatasetPrivacyError,
)

from app.services.recommendations.ml.privacy.feature_leakage import (
    FeatureLeakageDetector,
)


@dataclass(frozen=True, slots=True)
class DatasetPrivacyReport:
    """Dataset privacy validation result."""

    training_samples: int

    validation_samples: int

    training_users: int

    validation_users: int

    shared_users: int

    duplicate_training_pairs: int

    duplicate_validation_pairs: int

    feature_names_checked: tuple[str, ...]

    @property
    def is_safe(self) -> bool:

        return (
            self.shared_users == 0
            and self.duplicate_training_pairs == 0
            and self.duplicate_validation_pairs == 0
        )

    def to_dict(self) -> dict:

        return {
            "training_samples": self.training_samples,

            "validation_samples": self.validation_samples,

            "training_users": self.training_users,

            "validation_users": self.validation_users,

            "shared_users": self.shared_users,

            "duplicate_training_pairs": (
                self.duplicate_training_pairs
            ),

            "duplicate_validation_pairs": (
                self.duplicate_validation_pairs
            ),

            "feature_names_checked": list(
                self.feature_names_checked
            ),

            "is_safe": self.is_safe,
        }


class DatasetPrivacyValidator:
    """Validate privacy-related dataset constraints."""

    def __init__(
        self,
        config: PrivacyConfig | None = None,
        leakage_detector: FeatureLeakageDetector | None = None,
    ) -> None:

        self.config = config or PrivacyConfig()

        self.leakage_detector = (
            leakage_detector
            or FeatureLeakageDetector()
        )

    @staticmethod
    def _validate_identifiers(
        identifiers: Sequence[UUID],
        name: str,
    ) -> None:

        if not identifiers:

            raise DatasetPrivacyError(
                f"{name} cannot be empty."
            )

        if any(
            not isinstance(identifier, UUID)
            for identifier in identifiers
        ):

            raise DatasetPrivacyError(
                f"All {name} must be UUID objects."
            )

    @staticmethod
    def _count_duplicates(
        user_ids: Sequence[UUID],
        resource_ids: Sequence[UUID],
    ) -> int:

        pairs = list(
            zip(
                user_ids,
                resource_ids,
            )
        )

        return len(pairs) - len(set(pairs))

    def validate(
        self,
        training_user_ids: Sequence[UUID],
        training_resource_ids: Sequence[UUID],
        validation_user_ids: Sequence[UUID],
        validation_resource_ids: Sequence[UUID],
        feature_names: Sequence[str],
    ) -> DatasetPrivacyReport:

        self._validate_identifiers(
            training_user_ids,
            "Training user identifiers",
        )

        self._validate_identifiers(
            training_resource_ids,
            "Training resource identifiers",
        )

        self._validate_identifiers(
            validation_user_ids,
            "Validation user identifiers",
        )

        self._validate_identifiers(
            validation_resource_ids,
            "Validation resource identifiers",
        )

        if len(training_user_ids) != len(training_resource_ids):

            raise DatasetPrivacyError(
                "Training user and resource arrays must align."
            )

        if len(validation_user_ids) != len(validation_resource_ids):

            raise DatasetPrivacyError(
                "Validation user and resource arrays must align."
            )

        training_samples = len(training_user_ids)

        validation_samples = len(validation_user_ids)

        if (
            training_samples + validation_samples
            < self.config.minimum_dataset_samples
        ):

            raise DatasetPrivacyError(
                "Combined training and validation dataset "
                "is smaller than the configured minimum."
            )

        training_users = set(
            training_user_ids
        )

        validation_users = set(
            validation_user_ids
        )

        if (
            len(training_users)
            < self.config.minimum_distinct_users
        ):

            raise DatasetPrivacyError(
                "Insufficient distinct training users."
            )

        if (
            len(validation_users)
            < 1
        ):

            raise DatasetPrivacyError(
                "Validation data must contain at least one user."
            )

        shared_users = training_users.intersection(
            validation_users
        )

        if (
            self.config.require_user_separated_validation
            and shared_users
        ):

            raise DatasetPrivacyError(
                "User overlap detected between training "
                "and validation datasets."
            )

        duplicate_training_pairs = self._count_duplicates(
            training_user_ids,
            training_resource_ids,
        )

        duplicate_validation_pairs = self._count_duplicates(
            validation_user_ids,
            validation_resource_ids,
        )

        if duplicate_training_pairs:

            raise DatasetPrivacyError(
                "Duplicate user-resource pairs detected "
                "in training data."
            )

        if duplicate_validation_pairs:

            raise DatasetPrivacyError(
                "Duplicate user-resource pairs detected "
                "in validation data."
            )

        self.leakage_detector.validate(
            feature_names
        )

        return DatasetPrivacyReport(
            training_samples=training_samples,

            validation_samples=validation_samples,

            training_users=len(training_users),

            validation_users=len(validation_users),

            shared_users=len(shared_users),

            duplicate_training_pairs=duplicate_training_pairs,

            duplicate_validation_pairs=duplicate_validation_pairs,

            feature_names_checked=tuple(feature_names),
        )