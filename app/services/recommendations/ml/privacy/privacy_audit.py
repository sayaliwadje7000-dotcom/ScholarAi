"""Central privacy audit for ScholarAI recommendation ML."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence
from uuid import UUID

from app.services.recommendations.ml.privacy.data_sanitizer import (
    MetadataSanitizer,
)

from app.services.recommendations.ml.privacy.dataset_privacy import (
    DatasetPrivacyReport,
    DatasetPrivacyValidator,
)

from app.services.recommendations.ml.privacy.feature_leakage import (
    FeatureLeakageDetector,
    FeatureLeakageReport,
)

from app.services.recommendations.ml.privacy.privacy_config import (
    PrivacyConfig,
)


@dataclass(frozen=True, slots=True)
class PrivacyAuditResult:
    """Combined privacy audit output."""

    dataset_report: DatasetPrivacyReport

    feature_report: FeatureLeakageReport

    sanitized_metadata: dict[str, Any]

    @property
    def passed(self) -> bool:

        return (
            self.dataset_report.is_safe
            and self.feature_report.is_safe
        )

    def to_dict(self) -> dict[str, Any]:

        return {
            "passed": self.passed,

            "dataset_report": (
                self.dataset_report.to_dict()
            ),

            "feature_report": (
                self.feature_report.to_dict()
            ),

            "sanitized_metadata": self.sanitized_metadata,
        }


class RecommendationPrivacyAuditor:
    """Coordinate the recommendation ML privacy checks."""

    def __init__(
        self,
        config: PrivacyConfig | None = None,
    ) -> None:

        self.config = config or PrivacyConfig()

        self.leakage_detector = FeatureLeakageDetector()

        self.dataset_validator = DatasetPrivacyValidator(
            config=self.config,
            leakage_detector=self.leakage_detector,
        )

        self.metadata_sanitizer = MetadataSanitizer(
            config=self.config
        )

    def audit(
        self,
        training_user_ids: Sequence[UUID],
        training_resource_ids: Sequence[UUID],
        validation_user_ids: Sequence[UUID],
        validation_resource_ids: Sequence[UUID],
        feature_names: Sequence[str],
        metadata: Mapping[str, Any],
    ) -> PrivacyAuditResult:

        if not isinstance(metadata, Mapping):

            raise ValueError(
                "Audit metadata must be a mapping."
            )

        feature_report = self.leakage_detector.inspect(
            feature_names
        )

        dataset_report = self.dataset_validator.validate(
            training_user_ids=training_user_ids,
            training_resource_ids=training_resource_ids,
            validation_user_ids=validation_user_ids,
            validation_resource_ids=validation_resource_ids,
            feature_names=feature_names,
        )

        sanitized_metadata = self.metadata_sanitizer.sanitize(
            dict(metadata)
        )

        return PrivacyAuditResult(
            dataset_report=dataset_report,

            feature_report=feature_report,

            sanitized_metadata=sanitized_metadata,
        )