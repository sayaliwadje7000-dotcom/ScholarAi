from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from math import isfinite
from typing import Callable, Any

from app.schemas.external_resources import (
    ExternalResource,
    ExternalResourceType,
)


QUALITY_ALGORITHM_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class QualityWeights:
    """
    Configurable weights for resource quality evaluation.

    All weights must be non-negative and must sum to 1.
    """

    completeness: float = 0.35
    credibility: float = 0.35
    freshness: float = 0.30

    def __post_init__(self) -> None:
        values = (
            self.completeness,
            self.credibility,
            self.freshness,
        )

        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(value)
            or value < 0
            for value in values
        ):
            raise ValueError(
                "Quality weights must be finite, "
                "non-negative numbers."
            )

        if abs(sum(values) - 1.0) > 1e-9:
            raise ValueError(
                "Quality weights must sum to exactly 1.0."
            )


@dataclass(frozen=True, slots=True)
class FreshnessPolicy:
    """
    Half-life policy for different educational resource types.

    A half-life is the number of days after which the freshness
    score decreases to approximately 50.
    """

    half_life_days: dict[str, int]

    def __post_init__(self) -> None:
        if not isinstance(self.half_life_days, dict):
            raise TypeError(
                "half_life_days must be a dictionary."
            )

        for resource_type, days in self.half_life_days.items():
            if not isinstance(resource_type, str):
                raise TypeError(
                    "Resource type keys must be strings."
                )

            if (
                isinstance(days, bool)
                or not isinstance(days, int)
                or days <= 0
            ):
                raise ValueError(
                    "Freshness half-life values must "
                    "be positive integers."
                )


@dataclass(frozen=True, slots=True)
class ResourceQualityAssessment:
    """
    Immutable quality assessment result.

    Scores are represented on a 0–100 scale.
    """

    overall_score: float

    completeness_score: float

    credibility_score: float

    freshness_score: float

    algorithm_version: str

    evaluated_at: datetime

    flags: tuple[str, ...]

    def __post_init__(self) -> None:
        scores = (
            self.overall_score,
            self.completeness_score,
            self.credibility_score,
            self.freshness_score,
        )

        for score in scores:
            if (
                isinstance(score, bool)
                or not isinstance(score, (int, float))
                or not isfinite(score)
                or not 0 <= score <= 100
            ):
                raise ValueError(
                    "Quality scores must be finite "
                    "numbers between 0 and 100."
                )

        if (
            self.evaluated_at.tzinfo is None
            or self.evaluated_at.utcoffset() is None
        ):
            raise ValueError(
                "evaluated_at must be timezone-aware."
            )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the assessment into JSON-compatible metadata.
        """

        return {
            "overall_score": self.overall_score,
            "completeness_score": self.completeness_score,
            "credibility_score": self.credibility_score,
            "freshness_score": self.freshness_score,
            "algorithm_version": self.algorithm_version,
            "evaluated_at": self.evaluated_at.isoformat(),
            "flags": list(self.flags),
        }


class ResourceQualityAssessor:
    """
    Evaluate educational resources using three independent signals:

    1. Metadata completeness.
    2. Provider-level credibility.
    3. Publication-date freshness.

    This service does not perform relevance ranking or persistence.
    """

    DEFAULT_PROVIDER_CREDIBILITY = {
        "openalex": 0.90,
        "crossref": 0.90,
        "google_books": 0.82,
        "youtube": 0.65,
    }

    DEFAULT_FRESHNESS_POLICY = {
        ExternalResourceType.VIDEO.value: 730,
        ExternalResourceType.ARTICLE.value: 1825,
        ExternalResourceType.COURSE.value: 1095,
        ExternalResourceType.DOCUMENTATION.value: 1095,
        ExternalResourceType.TUTORIAL.value: 1460,
        ExternalResourceType.WEBSITE.value: 1095,
        ExternalResourceType.BOOK.value: 3650,
    }

    def __init__(
        self,
        weights: QualityWeights | None = None,
        provider_credibility: dict[str, float] | None = None,
        freshness_policy: FreshnessPolicy | None = None,
        unknown_provider_score: float = 0.50,
        unknown_publication_date_score: float = 50.0,
        clock: Callable[[], datetime] | None = None,
    ) -> None:

        self.weights = weights or QualityWeights()

        self.provider_credibility = (
            provider_credibility
            if provider_credibility is not None
            else dict(self.DEFAULT_PROVIDER_CREDIBILITY)
        )

        self.freshness_policy = freshness_policy or (
            FreshnessPolicy(
                half_life_days=dict(
                    self.DEFAULT_FRESHNESS_POLICY
                )
            )
        )

        self.unknown_provider_score = unknown_provider_score

        self.unknown_publication_date_score = (
            unknown_publication_date_score
        )

        self.clock = clock or (
            lambda: datetime.now(timezone.utc)
        )

        self._validate_configuration()

    # ---------------------------------------------------------
    # Configuration validation
    # ---------------------------------------------------------

    @staticmethod
    def _validate_score(
        name: str,
        value: float,
    ) -> None:

        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(value)
            or not 0 <= value <= 1
        ):
            raise ValueError(
                f"{name} must be between 0 and 1."
            )

    def _validate_configuration(self) -> None:

        self._validate_score(
            "unknown_provider_score",
            self.unknown_provider_score,
        )

        if (
            isinstance(
                self.unknown_publication_date_score,
                bool,
            )
            or not isinstance(
                self.unknown_publication_date_score,
                (int, float),
            )
            or not isfinite(
                self.unknown_publication_date_score
            )
            or not 0 <= self.unknown_publication_date_score <= 100
        ):
            raise ValueError(
                "unknown_publication_date_score "
                "must be between 0 and 100."
            )

        for provider, score in self.provider_credibility.items():

            if not isinstance(provider, str) or not provider.strip():
                raise ValueError(
                    "Provider names must be non-empty strings."
                )

            self._validate_score(
                f"Credibility score for {provider}",
                score,
            )

    # ---------------------------------------------------------
    # Date handling
    # ---------------------------------------------------------

    @staticmethod
    def _to_utc(value: datetime) -> datetime:

        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc)

    def _current_time(self) -> datetime:

        current = self.clock()

        if not isinstance(current, datetime):
            raise TypeError(
                "Clock must return a datetime."
            )

        return self._to_utc(current)

    # ---------------------------------------------------------
    # Metadata completeness
    # ---------------------------------------------------------

    @staticmethod
    def _has_value(value: Any) -> bool:

        if value is None:
            return False

        if isinstance(value, str):
            return bool(value.strip())

        if isinstance(value, (list, tuple, dict, set)):
            return len(value) > 0

        return True

    @classmethod
    def _completeness_score(
        cls,
        resource: ExternalResource,
    ) -> float:
        """
        Calculate metadata completeness on a 0–100 scale.

        The scoring weights below total 100.
        """

        checks = (
            (resource.title, 15),
            (resource.description, 20),
            (resource.authors, 10),
            (resource.subject, 10),
            (resource.language, 5),
            (resource.published_at, 15),
            (resource.license, 10),
            (resource.canonical_url, 10),
            (
                resource.access_type.value != "unknown",
                5,
            ),
        )

        score = 0.0

        for value, weight in checks:

            if isinstance(value, bool):
                present = value
            else:
                present = cls._has_value(value)

            if present:
                score += weight

        return round(score, 2)

    # ---------------------------------------------------------
    # Provider credibility
    # ---------------------------------------------------------

    def _credibility_score(
        self,
        resource: ExternalResource,
    ) -> float:
        """
        Return configured provider credibility on a 0–100 scale.

        Unknown providers receive a configurable neutral score.
        """

        provider = resource.provider.strip().casefold()

        normalized_scores = {
            name.strip().casefold(): score
            for name, score in self.provider_credibility.items()
        }

        score = normalized_scores.get(
            provider,
            self.unknown_provider_score,
        )

        return round(score * 100, 2)

    # ---------------------------------------------------------
    # Freshness evaluation
    # ---------------------------------------------------------

    def _freshness_score(
        self,
        resource: ExternalResource,
        current_time: datetime,
    ) -> tuple[float, tuple[str, ...]]:
        """
        Calculate freshness using exponential half-life decay.

        Formula:

            freshness = 100 * 0.5 ** (age_days / half_life_days)

        Missing dates receive a neutral unknown-date score.
        """

        if resource.published_at is None:
            return (
                float(self.unknown_publication_date_score),
                ("publication_date_missing",),
            )

        published_at = self._to_utc(
            resource.published_at
        )

        age_seconds = (
            current_time - published_at
        ).total_seconds()

        flags: list[str] = []

        if age_seconds < 0:
            flags.append("future_publication_date")

            # Do not reward future-dated content as fresh.
            return 50.0, tuple(flags)

        age_days = age_seconds / 86400

        resource_type = resource.resource_type.value

        half_life = self.freshness_policy.half_life_days.get(
            resource_type,
        )

        if half_life is None:
            half_life = 1095
            flags.append("default_freshness_policy_used")

        score = 100 * (
            0.5 ** (age_days / half_life)
        )

        if age_days > half_life:
            flags.append("older_than_freshness_half_life")

        return round(
            max(0.0, min(100.0, score)),
            2,
        ), tuple(flags)

    # ---------------------------------------------------------
    # Assessment
    # ---------------------------------------------------------

    def assess(
        self,
        resource: ExternalResource,
    ) -> ResourceQualityAssessment:

        if not isinstance(resource, ExternalResource):
            raise TypeError(
                "Expected an ExternalResource instance."
            )

        current_time = self._current_time()

        completeness = self._completeness_score(
            resource
        )

        credibility = self._credibility_score(
            resource
        )

        freshness, freshness_flags = (
            self._freshness_score(
                resource,
                current_time,
            )
        )

        overall = (
            completeness * self.weights.completeness
            + credibility * self.weights.credibility
            + freshness * self.weights.freshness
        )

        flags = list(freshness_flags)

        provider = resource.provider.strip().casefold()

        known_providers = {
            name.strip().casefold()
            for name in self.provider_credibility
        }

        if provider not in known_providers:
            flags.append("unknown_provider")

        return ResourceQualityAssessment(
            overall_score=round(overall, 2),
            completeness_score=completeness,
            credibility_score=credibility,
            freshness_score=freshness,
            algorithm_version=QUALITY_ALGORITHM_VERSION,
            evaluated_at=current_time,
            flags=tuple(sorted(set(flags))),
        )

    # ---------------------------------------------------------
    # Resource enrichment
    # ---------------------------------------------------------

    def assess_resource(
        self,
        resource: ExternalResource,
    ) -> ExternalResource:
        """
        Return a new resource containing quality metadata.

        The original resource and its metadata are not mutated.
        """

        assessment = self.assess(resource)

        metadata = dict(resource.metadata)

        metadata["quality_assessment"] = (
            assessment.to_dict()
        )

        return replace(
            resource,
            metadata=metadata,
        )

    def assess_many(
        self,
        resources: list[ExternalResource],
    ) -> list[ExternalResource]:
        """
        Assess multiple resources without changing their order.
        """

        if not isinstance(resources, list):
            raise TypeError(
                "Resources must be provided as a list."
            )

        return [
            self.assess_resource(resource)
            for resource in resources
        ]