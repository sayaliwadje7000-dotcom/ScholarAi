from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from typing import Any, Mapping
from uuid import UUID


class HybridContractError(ValueError):
    """Base exception for hybrid recommendation contract violations."""


class RecommendationComponent(str, Enum):
    """
    Identifies the recommendation engine that produced a result.
    """

    RULE_BASED = "rule_based"
    CONTENT_BASED = "content_based"
    MACHINE_LEARNING = "machine_learning"


class ComponentStatus(str, Enum):
    """
    Describes whether a recommendation component produced a usable score.
    """

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"


class ScoreDirection(str, Enum):
    """
    Describes the interpretation of a component's raw score.

    This is descriptive metadata. It does not normalize the score.
    """

    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"


def _validate_datetime(
    value: datetime,
    field_name: str,
) -> None:
    if not isinstance(value, datetime):
        raise HybridContractError(
            f"{field_name} must be a datetime."
        )

    if value.tzinfo is None or value.utcoffset() is None:
        raise HybridContractError(
            f"{field_name} must be timezone-aware."
        )


def _validate_non_empty_string(
    value: str,
    field_name: str,
) -> None:
    if not isinstance(value, str) or not value.strip():
        raise HybridContractError(
            f"{field_name} must be a non-empty string."
        )


def _validate_finite_number(
    value: float,
    field_name: str,
) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise HybridContractError(
            f"{field_name} must be a numeric value."
        )

    if not isfinite(float(value)):
        raise HybridContractError(
            f"{field_name} must be finite."
        )


@dataclass(frozen=True, slots=True)
class ComponentScore:
    """
    Raw score produced by an individual recommendation component.

    Raw scores are intentionally not restricted to [0, 1].

    Different engines may use different score ranges and semantics.
    Phase 15.3 is responsible for score normalization.
    """

    component: RecommendationComponent

    status: ComponentStatus

    value: float | None = None

    direction: ScoreDirection = ScoreDirection.HIGHER_IS_BETTER

    model_version: str | None = None

    reason: str | None = None

    calculated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        if not isinstance(
            self.component,
            RecommendationComponent,
        ):
            raise HybridContractError(
                "component must be a RecommendationComponent."
            )

        if not isinstance(
            self.status,
            ComponentStatus,
        ):
            raise HybridContractError(
                "status must be a ComponentStatus."
            )

        if not isinstance(
            self.direction,
            ScoreDirection,
        ):
            raise HybridContractError(
                "direction must be a ScoreDirection."
            )

        _validate_datetime(
            self.calculated_at,
            "calculated_at",
        )

        if self.status == ComponentStatus.AVAILABLE:
            if self.value is None:
                raise HybridContractError(
                    "An available component must contain a score."
                )

            _validate_finite_number(
                self.value,
                "value",
            )

        else:
            if self.value is not None:
                raise HybridContractError(
                    "Unavailable, failed, or non-applicable "
                    "components must not contain a score."
                )

        if self.model_version is not None:
            _validate_non_empty_string(
                self.model_version,
                "model_version",
            )

        if self.reason is not None:
            if not isinstance(self.reason, str):
                raise HybridContractError(
                    "reason must be a string or None."
                )


@dataclass(frozen=True, slots=True)
class RecommendationProvenance:
    """
    Records where a recommendation candidate originated.

    A resource can have multiple provenance records because
    different recommendation components may discover the same resource.
    """

    component: RecommendationComponent

    source_name: str

    source_id: str | None = None

    source_url: str | None = None

    retrieved_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        if not isinstance(
            self.component,
            RecommendationComponent,
        ):
            raise HybridContractError(
                "component must be a RecommendationComponent."
            )

        _validate_non_empty_string(
            self.source_name,
            "source_name",
        )

        if self.source_id is not None:
            _validate_non_empty_string(
                self.source_id,
                "source_id",
            )

        if self.source_url is not None:
            _validate_non_empty_string(
                self.source_url,
                "source_url",
            )

        _validate_datetime(
            self.retrieved_at,
            "retrieved_at",
        )


@dataclass(frozen=True, slots=True)
class HybridCandidate:
    """
    Unified internal representation of a recommendation candidate.

    The same resource may be discovered by multiple components.
    Candidate aggregation and deduplication will be implemented
    in Phase 15.4.
    """

    resource_id: UUID

    title: str

    resource_type: str

    component_scores: tuple[ComponentScore, ...]

    provenance: tuple[RecommendationProvenance, ...]

    canonical_url: str | None = None

    description: str | None = None

    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )

    discovered_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        if not isinstance(self.resource_id, UUID):
            raise HybridContractError(
                "resource_id must be a UUID."
            )

        _validate_non_empty_string(
            self.title,
            "title",
        )

        _validate_non_empty_string(
            self.resource_type,
            "resource_type",
        )

        if not isinstance(
            self.component_scores,
            tuple,
        ):
            raise HybridContractError(
                "component_scores must be a tuple."
            )

        if not isinstance(
            self.provenance,
            tuple,
        ):
            raise HybridContractError(
                "provenance must be a tuple."
            )

        for score in self.component_scores:
            if not isinstance(score, ComponentScore):
                raise HybridContractError(
                    "Every component score must be a ComponentScore."
                )

        for record in self.provenance:
            if not isinstance(
                record,
                RecommendationProvenance,
            ):
                raise HybridContractError(
                    "Every provenance entry must be "
                    "a RecommendationProvenance."
                )

        components = [
            score.component
            for score in self.component_scores
        ]

        if len(components) != len(set(components)):
            raise HybridContractError(
                "A candidate cannot contain multiple scores "
                "for the same component."
            )

        if self.canonical_url is not None:
            _validate_non_empty_string(
                self.canonical_url,
                "canonical_url",
            )

        if self.description is not None:
            if not isinstance(self.description, str):
                raise HybridContractError(
                    "description must be a string or None."
                )

        if not isinstance(self.metadata, Mapping):
            raise HybridContractError(
                "metadata must be a mapping."
            )

        _validate_datetime(
            self.discovered_at,
            "discovered_at",
        )

    def get_component_score(
        self,
        component: RecommendationComponent,
    ) -> ComponentScore | None:
        """
        Retrieve the score record for a specific component.
        """

        for score in self.component_scores:
            if score.component == component:
                return score

        return None

    def available_components(
        self,
    ) -> tuple[RecommendationComponent, ...]:
        """
        Return components that successfully produced a score.
        """

        return tuple(
            score.component
            for score in self.component_scores
            if score.status == ComponentStatus.AVAILABLE
        )

    def failed_components(
        self,
    ) -> tuple[RecommendationComponent, ...]:
        """
        Return components that failed during execution.
        """

        return tuple(
            score.component
            for score in self.component_scores
            if score.status == ComponentStatus.FAILED
        )


@dataclass(frozen=True, slots=True)
class HybridRecommendationBatch:
    """
    Represents a collection of unified recommendation candidates.

    This is an internal orchestration contract, not an API response.
    """

    request_id: UUID

    user_id: UUID

    candidates: tuple[HybridCandidate, ...]

    generated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, UUID):
            raise HybridContractError(
                "request_id must be a UUID."
            )

        if not isinstance(self.user_id, UUID):
            raise HybridContractError(
                "user_id must be a UUID."
            )

        if not isinstance(self.candidates, tuple):
            raise HybridContractError(
                "candidates must be a tuple."
            )

        for candidate in self.candidates:
            if not isinstance(candidate, HybridCandidate):
                raise HybridContractError(
                    "Every candidate must be a HybridCandidate."
                )

        _validate_datetime(
            self.generated_at,
            "generated_at",
        )