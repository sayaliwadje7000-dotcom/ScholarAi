"""Feature leakage detection for ScholarAI."""

from __future__ import annotations

import re

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from app.services.recommendations.ml.privacy.privacy_exceptions import (
    IdentifierLeakageError,
    TargetLeakageError,
    TemporalLeakageError,
)


@dataclass(frozen=True, slots=True)
class FeatureLeakageReport:
    """Results of a feature leakage inspection."""

    checked_features: tuple[str, ...]

    identifier_features: tuple[str, ...]

    target_features: tuple[str, ...]

    future_features: tuple[str, ...]

    @property
    def is_safe(self) -> bool:

        return not (
            self.identifier_features
            or self.target_features
            or self.future_features
        )

    def to_dict(self) -> dict[str, Any]:

        return {
            "checked_features": list(
                self.checked_features
            ),

            "identifier_features": list(
                self.identifier_features
            ),

            "target_features": list(
                self.target_features
            ),

            "future_features": list(
                self.future_features
            ),

            "is_safe": self.is_safe,
        }


class FeatureLeakageDetector:
    """Detect identifiers, target leakage and temporal leakage."""

    IDENTIFIER_PATTERNS = (
        re.compile(r"(^|_)(user|resource|document|session)_?id($|_)"),
        re.compile(r"(^|_)(email|phone|mobile|address)($|_)"),
    )

    TARGET_FEATURES = {
        "label",
        "target",
        "relevance_label",
        "is_relevant",
        "ground_truth",
        "ground_truth_label",
        "feedback_label",
        "future_click",
        "future_save",
        "future_completion",
        "post_recommendation_rating",
    }

    FUTURE_INDICATORS = (
        "future_",
        "after_prediction_",
        "post_prediction_",
        "post_recommendation_",
    )

    @staticmethod
    def _normalize(
        feature_name: str,
    ) -> str:

        return feature_name.strip().casefold()

    def _is_identifier(
        self,
        feature_name: str,
    ) -> bool:

        normalized = self._normalize(
            feature_name
        )

        return any(
            pattern.search(normalized)
            for pattern in self.IDENTIFIER_PATTERNS
        )

    def _is_target(
        self,
        feature_name: str,
    ) -> bool:

        normalized = self._normalize(
            feature_name
        )

        return normalized in self.TARGET_FEATURES

    def _is_future(
        self,
        feature_name: str,
    ) -> bool:

        normalized = self._normalize(
            feature_name
        )

        return any(
            normalized.startswith(prefix)
            for prefix in self.FUTURE_INDICATORS
        )

    def inspect(
        self,
        feature_names: Sequence[str],
    ) -> FeatureLeakageReport:

        if isinstance(feature_names, (str, bytes)):

            raise ValueError(
                "Feature names must be a sequence of strings."
            )

        if not feature_names:

            raise ValueError(
                "At least one feature name is required."
            )

        if any(
            not isinstance(name, str) or not name.strip()
            for name in feature_names
        ):

            raise ValueError(
                "Feature names must be non-empty strings."
            )

        if len(set(feature_names)) != len(feature_names):

            raise ValueError(
                "Feature names must be unique."
            )

        identifier_features = tuple(
            name
            for name in feature_names
            if self._is_identifier(name)
        )

        target_features = tuple(
            name
            for name in feature_names
            if self._is_target(name)
        )

        future_features = tuple(
            name
            for name in feature_names
            if self._is_future(name)
        )

        return FeatureLeakageReport(
            checked_features=tuple(feature_names),

            identifier_features=identifier_features,

            target_features=target_features,

            future_features=future_features,
        )

    def validate(
        self,
        feature_names: Sequence[str],
    ) -> FeatureLeakageReport:

        report = self.inspect(
            feature_names
        )

        if report.identifier_features:

            raise IdentifierLeakageError(
                "Identifier fields cannot be used as model features: "
                + ", ".join(report.identifier_features)
            )

        if report.target_features:

            raise TargetLeakageError(
                "Target fields cannot be used as model features: "
                + ", ".join(report.target_features)
            )

        if report.future_features:

            raise TemporalLeakageError(
                "Future-derived features cannot be used: "
                + ", ".join(report.future_features)
            )

        return report

    def validate_temporal_features(
        self,
        feature_timestamps: Mapping[str, datetime],
        prediction_at: datetime,
    ) -> None:
        """
        Ensure every feature timestamp is no later than prediction_at.

        All timestamps must be timezone-aware.
        """

        if prediction_at.tzinfo is None:

            raise ValueError(
                "prediction_at must be timezone-aware."
            )

        if prediction_at.utcoffset() is None:

            raise ValueError(
                "prediction_at must have a valid UTC offset."
            )

        prediction_time = prediction_at.astimezone(
            timezone.utc
        )

        for feature_name, feature_time in feature_timestamps.items():

            if not isinstance(feature_name, str):

                raise ValueError(
                    "Feature timestamp keys must be strings."
                )

            if not isinstance(feature_time, datetime):

                raise ValueError(
                    f"Invalid timestamp for feature {feature_name}."
                )

            if feature_time.tzinfo is None:

                raise ValueError(
                    f"Feature {feature_name} has a naive timestamp."
                )

            if feature_time.utcoffset() is None:

                raise ValueError(
                    f"Feature {feature_name} has an invalid UTC offset."
                )

            normalized_time = feature_time.astimezone(
                timezone.utc
            )

            if normalized_time > prediction_time:

                raise TemporalLeakageError(
                    f"Feature {feature_name} was recorded after "
                    "the prediction timestamp."
                )