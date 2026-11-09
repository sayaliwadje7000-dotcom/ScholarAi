from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from types import MappingProxyType
from typing import Mapping

from app.services.recommendations.hybrid.contracts import (
    ComponentScore,
    ComponentStatus,
    HybridCandidate,
    RecommendationComponent,
    ScoreDirection,
)


class HybridScoringError(ValueError):
    """Base exception for hybrid scoring errors."""


class ScoreNormalizationError(HybridScoringError):
    """Raised when a component score cannot be normalized."""


class WeightConfigurationError(HybridScoringError):
    """Raised when hybrid weights are invalid."""


class HybridAggregationError(HybridScoringError):
    """Raised when hybrid aggregation cannot be performed."""


class OutOfRangePolicy(str):
    """
    Defines how raw values outside configured normalization
    bounds should be handled.
    """

    CLAMP = "clamp"
    REJECT = "reject"


@dataclass(frozen=True, slots=True)
class ScoreNormalizationConfig:
    """
    Defines the expected raw-score range for one component.

    The configured range must reflect the actual semantics of
    the component's output. It must not be guessed from a score
    observed in a single recommendation request.
    """

    minimum: float

    maximum: float

    out_of_range_policy: str = OutOfRangePolicy.REJECT

    def __post_init__(self) -> None:
        for name, value in (
            ("minimum", self.minimum),
            ("maximum", self.maximum),
        ):
            if isinstance(value, bool) or not isinstance(
                value,
                (int, float),
            ):
                raise ScoreNormalizationError(
                    f"{name} must be numeric."
                )

            if not isfinite(float(value)):
                raise ScoreNormalizationError(
                    f"{name} must be finite."
                )

        if self.minimum >= self.maximum:
            raise ScoreNormalizationError(
                "minimum must be strictly less than maximum."
            )

        if self.out_of_range_policy not in (
            OutOfRangePolicy.CLAMP,
            OutOfRangePolicy.REJECT,
        ):
            raise ScoreNormalizationError(
                "Unsupported out-of-range policy."
            )


@dataclass(frozen=True, slots=True)
class HybridWeightConfig:
    """
    Stores the configured contribution of each recommendation
    component.

    Weights are normalized during aggregation. They do not need
    to sum to exactly one at construction time.
    """

    weights: Mapping[
        RecommendationComponent,
        float,
    ] = field(
        default_factory=lambda: {
            RecommendationComponent.RULE_BASED: 0.30,
            RecommendationComponent.CONTENT_BASED: 0.30,
            RecommendationComponent.MACHINE_LEARNING: 0.40,
        }
    )

    def __post_init__(self) -> None:
        if not isinstance(self.weights, Mapping):
            raise WeightConfigurationError(
                "weights must be a mapping."
            )

        if not self.weights:
            raise WeightConfigurationError(
                "At least one component weight is required."
            )

        validated: dict[RecommendationComponent, float] = {}

        for component, weight in self.weights.items():
            if not isinstance(
                component,
                RecommendationComponent,
            ):
                raise WeightConfigurationError(
                    "Every weight key must be a RecommendationComponent."
                )

            if isinstance(weight, bool) or not isinstance(
                weight,
                (int, float),
            ):
                raise WeightConfigurationError(
                    f"Weight for {component.value} must be numeric."
                )

            if not isfinite(float(weight)):
                raise WeightConfigurationError(
                    f"Weight for {component.value} must be finite."
                )

            if weight < 0:
                raise WeightConfigurationError(
                    f"Weight for {component.value} cannot be negative."
                )

            validated[component] = float(weight)

        if not any(value > 0 for value in validated.values()):
            raise WeightConfigurationError(
                "At least one component weight must be positive."
            )

        object.__setattr__(
            self,
            "weights",
            MappingProxyType(validated),
        )


@dataclass(frozen=True, slots=True)
class NormalizedComponentScore:
    """
    Preserves a raw component score alongside its normalized value.
    """

    component: RecommendationComponent

    raw_score: float

    normalized_score: float

    configured_minimum: float

    configured_maximum: float

    direction: ScoreDirection

    was_clamped: bool = False

    def __post_init__(self) -> None:
        for name, value in (
            ("raw_score", self.raw_score),
            ("normalized_score", self.normalized_score),
            ("configured_minimum", self.configured_minimum),
            ("configured_maximum", self.configured_maximum),
        ):
            if isinstance(value, bool) or not isinstance(
                value,
                (int, float),
            ):
                raise ScoreNormalizationError(
                    f"{name} must be numeric."
                )

            if not isfinite(float(value)):
                raise ScoreNormalizationError(
                    f"{name} must be finite."
                )

        if not 0.0 <= self.normalized_score <= 1.0:
            raise ScoreNormalizationError(
                "normalized_score must be between zero and one."
            )

        if self.configured_minimum >= self.configured_maximum:
            raise ScoreNormalizationError(
                "Invalid configured normalization bounds."
            )


@dataclass(frozen=True, slots=True)
class ComponentContribution:
    """
    Describes how a normalized component score contributes
    to the final hybrid score.
    """

    component: RecommendationComponent

    normalized_score: float

    configured_weight: float

    effective_weight: float

    weighted_contribution: float

    def __post_init__(self) -> None:
        values = (
            self.normalized_score,
            self.configured_weight,
            self.effective_weight,
            self.weighted_contribution,
        )

        for value in values:
            if not isfinite(float(value)):
                raise HybridAggregationError(
                    "Component contribution values must be finite."
                )

        if not 0.0 <= self.normalized_score <= 1.0:
            raise HybridAggregationError(
                "Normalized component score must be between zero and one."
            )

        if self.configured_weight < 0:
            raise HybridAggregationError(
                "Configured weight cannot be negative."
            )

        if self.effective_weight < 0:
            raise HybridAggregationError(
                "Effective weight cannot be negative."
            )


@dataclass(frozen=True, slots=True)
class HybridScoreResult:
    """
    Complete score calculation result for one candidate.

    The result preserves raw scores, normalized scores,
    configured weights and effective contributions.
    """

    resource_id: object

    hybrid_score: float

    normalized_scores: tuple[NormalizedComponentScore, ...]

    contributions: tuple[ComponentContribution, ...]

    available_components: tuple[RecommendationComponent, ...]

    excluded_components: tuple[RecommendationComponent, ...]

    configured_weight_total: float

    effective_weight_total: float

    def __post_init__(self) -> None:
        if not isfinite(float(self.hybrid_score)):
            raise HybridAggregationError(
                "hybrid_score must be finite."
            )

        if not 0.0 <= self.hybrid_score <= 1.0:
            raise HybridAggregationError(
                "hybrid_score must be between zero and one."
            )

        if (
            not isfinite(float(self.configured_weight_total))
            or self.configured_weight_total <= 0.0
        ):
            raise HybridAggregationError(
                "configured_weight_total must be finite and positive."
            )

        if not isfinite(float(self.effective_weight_total)):
            raise HybridAggregationError(
                "effective_weight_total must be finite."
            )

        if abs(self.effective_weight_total - 1.0) > 1e-9:
            raise HybridAggregationError(
                "Effective weights must sum to one."
            )


class HybridScoreNormalizer:
    """
    Normalizes raw component scores using explicitly configured
    component-specific bounds.

    Min-max normalization:

        normalized = (raw - minimum) / (maximum - minimum)

    For lower-is-better scores:

        normalized = 1 - normalized

    The final normalized result is always between zero and one.
    """

    def __init__(
        self,
        configurations: Mapping[
            RecommendationComponent,
            ScoreNormalizationConfig,
        ],
    ) -> None:
        if not isinstance(configurations, Mapping):
            raise ScoreNormalizationError(
                "configurations must be a mapping."
            )

        if not configurations:
            raise ScoreNormalizationError(
                "At least one normalization configuration is required."
            )

        validated = {}

        for component, configuration in configurations.items():
            if not isinstance(
                component,
                RecommendationComponent,
            ):
                raise ScoreNormalizationError(
                    "Invalid component in normalization configuration."
                )

            if not isinstance(
                configuration,
                ScoreNormalizationConfig,
            ):
                raise ScoreNormalizationError(
                    "Invalid score normalization configuration."
                )

            validated[component] = configuration

        self._configurations = MappingProxyType(validated)

    @property
    def configurations(
        self,
    ) -> Mapping[
        RecommendationComponent,
        ScoreNormalizationConfig,
    ]:
        return self._configurations

    def normalize(
        self,
        score: ComponentScore,
    ) -> NormalizedComponentScore:
        if not isinstance(score, ComponentScore):
            raise ScoreNormalizationError(
                "score must be a ComponentScore."
            )

        if score.status != ComponentStatus.AVAILABLE:
            raise ScoreNormalizationError(
                "Only available component scores can be normalized."
            )

        if score.value is None:
            raise ScoreNormalizationError(
                "Available component score cannot be None."
            )

        configuration = self._configurations.get(
            score.component
        )

        if configuration is None:
            raise ScoreNormalizationError(
                f"No normalization configuration exists for "
                f"{score.component.value}."
            )

        raw_score = float(score.value)

        minimum = float(configuration.minimum)
        maximum = float(configuration.maximum)

        was_clamped = False

        if raw_score < minimum or raw_score > maximum:
            if (
                configuration.out_of_range_policy
                == OutOfRangePolicy.REJECT
            ):
                raise ScoreNormalizationError(
                    f"Score {raw_score} for {score.component.value} "
                    f"is outside the configured range "
                    f"[{minimum}, {maximum}]."
                )

            raw_score = min(
                max(raw_score, minimum),
                maximum,
            )

            was_clamped = True

        normalized = (
            (raw_score - minimum)
            / (maximum - minimum)
        )

        if score.direction == ScoreDirection.LOWER_IS_BETTER:
            normalized = 1.0 - normalized

        normalized = min(
            max(normalized, 0.0),
            1.0,
        )

        return NormalizedComponentScore(
            component=score.component,
            raw_score=float(score.value),
            normalized_score=normalized,
            configured_minimum=minimum,
            configured_maximum=maximum,
            direction=score.direction,
            was_clamped=was_clamped,
        )


class HybridWeightingEngine:
    """
    Combines available normalized component scores.

    Missing, unavailable, failed and non-applicable components
    do not contribute a fabricated zero.

    Effective weights are recalculated across available components.
    """

    def __init__(
        self,
        weight_config: HybridWeightConfig,
    ) -> None:
        if not isinstance(
            weight_config,
            HybridWeightConfig,
        ):
            raise WeightConfigurationError(
                "weight_config must be a HybridWeightConfig."
            )

        self._weight_config = weight_config

    @property
    def weight_config(self) -> HybridWeightConfig:
        return self._weight_config

    def aggregate(
        self,
        candidate: HybridCandidate,
        normalized_scores: tuple[
            NormalizedComponentScore,
            ...,
        ],
    ) -> HybridScoreResult:
        if not isinstance(candidate, HybridCandidate):
            raise HybridAggregationError(
                "candidate must be a HybridCandidate."
            )

        if not isinstance(normalized_scores, tuple):
            raise HybridAggregationError(
                "normalized_scores must be a tuple."
            )

        normalized_by_component: dict[
            RecommendationComponent,
            NormalizedComponentScore,
        ] = {}

        for score in normalized_scores:
            if not isinstance(score, NormalizedComponentScore):
                raise HybridAggregationError(
                    "Invalid normalized score object."
                )

            if not isinstance(score.component, RecommendationComponent):
                raise HybridAggregationError(
                    "Normalized score has an invalid component."
                )

            if score.component in normalized_by_component:
                raise HybridAggregationError(
                    "Duplicate normalized component score."
                )

            normalized_by_component[score.component] = score

        candidate_available = {
            item.component
            for item in candidate.component_scores
            if item.status == ComponentStatus.AVAILABLE
        }

        positive_weight_components = {
            component
            for component, weight in self._weight_config.weights.items()
            if weight > 0.0
        }

        expected_components = (
            candidate_available & positive_weight_components
        )

        if set(normalized_by_component) != expected_components:
            raise HybridAggregationError(
                "Normalized scores must match all and only "
                "available candidate components with positive "
                "configured weights."
            )

        if not expected_components:
            raise HybridAggregationError(
                "No available component has a positive configured weight."
            )

        configured_weight_total = sum(
            self._weight_config.weights[component]
            for component in expected_components
        )

        if (
            not isfinite(configured_weight_total)
            or configured_weight_total <= 0.0
        ):
            raise HybridAggregationError(
                "Configured weight total must be finite and positive."
            )

        contributions: list[ComponentContribution] = []
        hybrid_score = 0.0

        ordered_components = sorted(
            expected_components,
            key=lambda component: component.value,
        )

        for component in ordered_components:
            normalized = normalized_by_component[component]
            configured_weight = self._weight_config.weights[component]
            effective_weight = configured_weight / configured_weight_total
            weighted_contribution = (
                normalized.normalized_score * effective_weight
            )
            hybrid_score += weighted_contribution

            contributions.append(
                ComponentContribution(
                    component=component,
                    normalized_score=normalized.normalized_score,
                    configured_weight=configured_weight,
                    effective_weight=effective_weight,
                    weighted_contribution=weighted_contribution,
                )
            )

        excluded_components = tuple(
            sorted(
                (
                    item.component
                    for item in candidate.component_scores
                    if item.component not in expected_components
                ),
                key=lambda component: component.value,
            )
        )

        return HybridScoreResult(
            resource_id=candidate.resource_id,
            hybrid_score=hybrid_score,
            normalized_scores=tuple(
                normalized_by_component[component]
                for component in ordered_components
            ),
            contributions=tuple(contributions),
            available_components=tuple(ordered_components),
            excluded_components=excluded_components,
            configured_weight_total=configured_weight_total,
            effective_weight_total=sum(
                item.effective_weight for item in contributions
            ),
        )

class HybridScoringPipeline:
    """
    Coordinates normalization and hybrid aggregation.

    It does not generate candidates, deduplicate resources,
    apply eligibility filters or rank recommendations.
    Those responsibilities belong to later Phase 15 subphases.
    """

    def __init__(
        self,
        normalizer: HybridScoreNormalizer,
        weighting_engine: HybridWeightingEngine,
    ) -> None:
        if not isinstance(
            normalizer,
            HybridScoreNormalizer,
        ):
            raise HybridScoringError(
                "normalizer must be a HybridScoreNormalizer."
            )

        if not isinstance(
            weighting_engine,
            HybridWeightingEngine,
        ):
            raise HybridScoringError(
                "weighting_engine must be a HybridWeightingEngine."
            )

        self._normalizer = normalizer
        self._weighting_engine = weighting_engine

    def score(
        self,
        candidate: HybridCandidate,
    ) -> HybridScoreResult:
        if not isinstance(candidate, HybridCandidate):
            raise HybridScoringError(
                "candidate must be a HybridCandidate."
            )

        normalized_scores = []

        for component_score in candidate.component_scores:
            if component_score.status != ComponentStatus.AVAILABLE:
                continue

            # A zero-weight component does not need normalization
            # for the current aggregation configuration.
            configured_weight = (
                self._weighting_engine.weight_config.weights.get(
                    component_score.component,
                    0.0,
                )
            )

            if configured_weight <= 0.0:
                continue

            normalized_scores.append(
                self._normalizer.normalize(
                    component_score
                )
            )

        return self._weighting_engine.aggregate(
            candidate=candidate,
            normalized_scores=tuple(normalized_scores),
        )
