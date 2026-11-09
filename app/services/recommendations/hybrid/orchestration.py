"""Resilient orchestration for hybrid recommendations.

Coordinates rule-based, content-based and ML recommendation
providers while isolating component failures.

The orchestration layer delegates candidate aggregation,
score calculation, eligibility filtering and ranking to the
existing Phase 15 pipelines.
"""

from __future__ import annotations

import logging

from dataclasses import dataclass, replace
from enum import Enum
from time import perf_counter
from typing import Callable, Mapping, Sequence
from uuid import UUID

from app.services.recommendations.hybrid.aggregation import (
    CandidateAggregationError,
    HybridCandidateAggregator,
)
from app.services.recommendations.hybrid.contracts import (
    ComponentScore,
    ComponentStatus,
    HybridCandidate,
    RecommendationComponent,
    ScoreDirection,
)
from app.services.recommendations.hybrid.filtering import (
    EligibilityDecision,
    HybridFilteringPipeline,
    FilteringResult,
)
from app.services.recommendations.hybrid.ranking import (
    HybridRankingPipeline,
    HybridRankingResponse,
)
from app.services.recommendations.hybrid.scoring import (
    HybridScoringError,
    HybridScoringPipeline,
)


logger = logging.getLogger(__name__)


class HybridOrchestrationError(RuntimeError):
    """Base exception for hybrid orchestration failures."""


class ProviderConfigurationError(HybridOrchestrationError):
    """Raised when provider configuration is invalid."""


class ProviderOutputError(HybridOrchestrationError):
    """Raised when a provider returns malformed output."""


class EligibilityResolutionError(HybridOrchestrationError):
    """Raised when eligibility decisions cannot be resolved."""


class ComponentExecutionStatus(str, Enum):
    """Execution status of an individual recommendation provider."""

    SUCCESS = "success"
    EMPTY = "empty"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass(frozen=True, slots=True)
class HybridRequestContext:
    """Context supplied to recommendation providers.

    The context is intentionally generic at this stage. It can
    carry the user's learning intent, filters and request metadata
    without coupling the orchestration layer to a particular API.
    """

    user_id: UUID
    query: str
    filters: Mapping[str, object]
    metadata: Mapping[str, object]

    def __post_init__(self) -> None:
        if not isinstance(self.user_id, UUID):
            raise HybridOrchestrationError(
                "user_id must be a UUID."
            )

        if not isinstance(self.query, str) or not self.query.strip():
            raise HybridOrchestrationError(
                "query must be a non-empty string."
            )

        if not isinstance(self.filters, Mapping):
            raise HybridOrchestrationError(
                "filters must be a mapping."
            )

        if not isinstance(self.metadata, Mapping):
            raise HybridOrchestrationError(
                "metadata must be a mapping."
            )


@dataclass(frozen=True, slots=True)
class HybridComponentProvider:
    """Injectable candidate provider for one recommendation component."""

    component: RecommendationComponent

    discover: Callable[
        [HybridRequestContext],
        Sequence[HybridCandidate],
    ]

    enabled: bool = True

    def __post_init__(self) -> None:
        if not isinstance(
            self.component,
            RecommendationComponent,
        ):
            raise ProviderConfigurationError(
                "component must be a RecommendationComponent."
            )

        if not callable(self.discover):
            raise ProviderConfigurationError(
                "discover must be callable."
            )

        if not isinstance(self.enabled, bool):
            raise ProviderConfigurationError(
                "enabled must be a boolean."
            )


@dataclass(frozen=True, slots=True)
class ComponentExecutionReport:
    """Observable execution result for one component."""

    component: RecommendationComponent
    status: ComponentExecutionStatus
    candidate_count: int
    duration_ms: float
    error_type: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.component,
            RecommendationComponent,
        ):
            raise HybridOrchestrationError(
                "Invalid component execution report component."
            )

        if not isinstance(
            self.status,
            ComponentExecutionStatus,
        ):
            raise HybridOrchestrationError(
                "Invalid component execution status."
            )

        if self.candidate_count < 0:
            raise HybridOrchestrationError(
                "candidate_count cannot be negative."
            )

        if self.duration_ms < 0:
            raise HybridOrchestrationError(
                "duration_ms cannot be negative."
            )

        if self.status == ComponentExecutionStatus.FAILED:
            if not self.error_type or not self.error_message:
                raise HybridOrchestrationError(
                    "Failed component reports require error details."
                )


@dataclass(frozen=True, slots=True)
class HybridOrchestrationResult:
    """Complete result of one hybrid recommendation request."""

    request_id: UUID
    user_id: UUID

    ranked_candidates: tuple

    filtering_results: tuple[FilteringResult, ...]

    component_reports: tuple[ComponentExecutionReport, ...]

    total_candidates_discovered: int
    total_candidates_after_deduplication: int

    total_candidates_scored: int
    total_candidates_accepted: int
    total_candidates_returned: int

    duration_ms: float

    fallback_used: bool

    warnings: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, UUID):
            raise HybridOrchestrationError(
                "request_id must be a UUID."
            )

        if not isinstance(self.user_id, UUID):
            raise HybridOrchestrationError(
                "user_id must be a UUID."
            )

        counts = (
            self.total_candidates_discovered,
            self.total_candidates_after_deduplication,
            self.total_candidates_scored,
            self.total_candidates_accepted,
            self.total_candidates_returned,
        )

        if any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            for value in counts
        ):
            raise HybridOrchestrationError(
                "Candidate counts must be non-negative integers."
            )

        if self.total_candidates_after_deduplication > (
            self.total_candidates_discovered
        ):
            raise HybridOrchestrationError(
                "Deduplicated count cannot exceed discovered count."
            )

        if self.total_candidates_returned > (
            self.total_candidates_accepted
        ):
            raise HybridOrchestrationError(
                "Returned count cannot exceed accepted count."
            )

        if self.duration_ms < 0:
            raise HybridOrchestrationError(
                "duration_ms cannot be negative."
            )


class HybridRecommendationOrchestrator:
    """Coordinates the complete resilient hybrid pipeline."""

    REQUIRED_COMPONENTS = (
        RecommendationComponent.RULE_BASED,
        RecommendationComponent.CONTENT_BASED,
        RecommendationComponent.MACHINE_LEARNING,
    )

    def __init__(
        self,
        providers: Sequence[HybridComponentProvider],
        candidate_aggregator: HybridCandidateAggregator,
        scoring_pipeline: HybridScoringPipeline,
        filtering_pipeline: HybridFilteringPipeline,
        ranking_pipeline: HybridRankingPipeline,
        eligibility_resolver: Callable[
            [tuple[HybridCandidate, ...], HybridRequestContext],
            Mapping[UUID, EligibilityDecision],
        ],
    ) -> None:

        if not isinstance(providers, Sequence):
            raise ProviderConfigurationError(
                "providers must be a sequence."
            )

        if not providers:
            raise ProviderConfigurationError(
                "At least one provider must be configured."
            )

        if not isinstance(
            candidate_aggregator,
            HybridCandidateAggregator,
        ):
            raise ProviderConfigurationError(
                "Invalid candidate aggregator."
            )

        if not isinstance(
            scoring_pipeline,
            HybridScoringPipeline,
        ):
            raise ProviderConfigurationError(
                "Invalid scoring pipeline."
            )

        if not isinstance(
            filtering_pipeline,
            HybridFilteringPipeline,
        ):
            raise ProviderConfigurationError(
                "Invalid filtering pipeline."
            )

        if not isinstance(
            ranking_pipeline,
            HybridRankingPipeline,
        ):
            raise ProviderConfigurationError(
                "Invalid ranking pipeline."
            )

        if not callable(eligibility_resolver):
            raise ProviderConfigurationError(
                "eligibility_resolver must be callable."
            )

        validated_providers: dict[
            RecommendationComponent,
            HybridComponentProvider,
        ] = {}

        for provider in providers:
            if not isinstance(
                provider,
                HybridComponentProvider,
            ):
                raise ProviderConfigurationError(
                    "Every provider must be a HybridComponentProvider."
                )

            if provider.component in validated_providers:
                raise ProviderConfigurationError(
                    f"Duplicate provider for {provider.component.value}."
                )

            validated_providers[provider.component] = provider

        self._providers = validated_providers
        self._candidate_aggregator = candidate_aggregator
        self._scoring_pipeline = scoring_pipeline
        self._filtering_pipeline = filtering_pipeline
        self._ranking_pipeline = ranking_pipeline
        self._eligibility_resolver = eligibility_resolver

    def _execute_provider(
        self,
        provider: HybridComponentProvider,
        context: HybridRequestContext,
    ) -> tuple[
        tuple[HybridCandidate, ...],
        ComponentExecutionReport,
    ]:

        started_at = perf_counter()

        if not provider.enabled:
            return (
                (),
                ComponentExecutionReport(
                    component=provider.component,
                    status=ComponentExecutionStatus.DISABLED,
                    candidate_count=0,
                    duration_ms=0.0,
                ),
            )

        try:
            output = provider.discover(context)

            if isinstance(output, (str, bytes, Mapping)):
                raise ProviderOutputError(
                    "Provider output must be a sequence of candidates."
                )

            if not isinstance(output, Sequence):
                raise ProviderOutputError(
                    "Provider output must be a sequence."
                )

            candidates = tuple(output)

            for candidate in candidates:
                if not isinstance(candidate, HybridCandidate):
                    raise ProviderOutputError(
                        "Provider returned a non-HybridCandidate object."
                    )

                matching_scores = [
                    score
                    for score in candidate.component_scores
                    if score.component == provider.component
                ]

                if len(matching_scores) != 1:
                    raise ProviderOutputError(
                        f"Candidate {candidate.resource_id} must contain "
                        f"exactly one score for {provider.component.value}."
                    )

                if matching_scores[0].status != ComponentStatus.AVAILABLE:
                    raise ProviderOutputError(
                        f"Provider {provider.component.value} returned "
                        "a candidate without an available component score."
                    )

            duration_ms = (
                perf_counter() - started_at
            ) * 1000.0

            status = (
                ComponentExecutionStatus.SUCCESS
                if candidates
                else ComponentExecutionStatus.EMPTY
            )

            return (
                candidates,
                ComponentExecutionReport(
                    component=provider.component,
                    status=status,
                    candidate_count=len(candidates),
                    duration_ms=duration_ms,
                ),
            )

        except Exception as exc:
            duration_ms = (
                perf_counter() - started_at
            ) * 1000.0

            logger.exception(
                "Hybrid recommendation provider failed: %s",
                provider.component.value,
            )

            return (
                (),
                ComponentExecutionReport(
                    component=provider.component,
                    status=ComponentExecutionStatus.FAILED,
                    candidate_count=0,
                    duration_ms=duration_ms,
                    error_type=type(exc).__name__,
                    error_message=str(exc)[:500],
                ),
            )

    @staticmethod
    def _add_missing_component_statuses(
        candidates: tuple[HybridCandidate, ...],
        reports: tuple[ComponentExecutionReport, ...],
    ) -> tuple[HybridCandidate, ...]:
        """Add explicit unavailable/failed/not-applicable statuses.

        This preserves component-level diagnostics for every
        candidate, including components that did not return it.
        """

        report_by_component = {
            report.component: report
            for report in reports
        }

        enriched: list[HybridCandidate] = []

        for candidate in candidates:
            existing = {
                score.component: score
                for score in candidate.component_scores
            }

            updated_scores = list(candidate.component_scores)

            for component in HybridRecommendationOrchestrator.REQUIRED_COMPONENTS:
                if component in existing:
                    continue

                report = report_by_component.get(component)

                if report is None:
                    status = ComponentStatus.NOT_APPLICABLE
                    reason = "No provider was configured."

                elif report.status == ComponentExecutionStatus.FAILED:
                    status = ComponentStatus.FAILED
                    reason = (
                        report.error_message
                        or "Component execution failed."
                    )

                elif report.status == ComponentExecutionStatus.DISABLED:
                    status = ComponentStatus.UNAVAILABLE
                    reason = "Component provider is disabled."

                else:
                    status = ComponentStatus.NOT_APPLICABLE
                    reason = (
                        "Component did not produce this candidate."
                    )

                updated_scores.append(
                    ComponentScore(
                        component=component,
                        status=status,
                        value=None,
                        direction=ScoreDirection.HIGHER_IS_BETTER,
                        reason=reason,
                    )
                )

            enriched.append(
                replace(
                    candidate,
                    component_scores=tuple(updated_scores),
                )
            )

        return tuple(enriched)

    def _resolve_eligibility(
        self,
        candidates: tuple[HybridCandidate, ...],
        context: HybridRequestContext,
    ) -> Mapping[UUID, EligibilityDecision]:

        try:
            decisions = self._eligibility_resolver(
                candidates,
                context,
            )

        except Exception as exc:
            raise EligibilityResolutionError(
                "Eligibility resolution failed."
            ) from exc

        if not isinstance(decisions, Mapping):
            raise EligibilityResolutionError(
                "Eligibility resolver must return a mapping."
            )

        expected_ids = {
            candidate.resource_id
            for candidate in candidates
        }

        if set(decisions.keys()) != expected_ids:
            raise EligibilityResolutionError(
                "Eligibility decisions must match candidate IDs exactly."
            )

        for resource_id, decision in decisions.items():
            if not isinstance(decision, EligibilityDecision):
                raise EligibilityResolutionError(
                    "Eligibility resolver returned an invalid decision."
                )

            if decision.resource_id != resource_id:
                raise EligibilityResolutionError(
                    "Eligibility decision resource ID mismatch."
                )

        return decisions

    def execute(
        self,
        context: HybridRequestContext,
        limit: int | None = None,
    ) -> HybridOrchestrationResult:
        """Execute the complete resilient recommendation pipeline."""

        if not isinstance(context, HybridRequestContext):
            raise HybridOrchestrationError(
                "context must be a HybridRequestContext."
            )

        started_at = perf_counter()

        request_id = UUID(
            str(context.metadata.get("request_id"))
        ) if context.metadata.get("request_id") else UUID(
            "00000000-0000-0000-0000-000000000000"
        )

        warnings: list[str] = []

        candidate_collections: list[
            tuple[HybridCandidate, ...]
        ] = []

        reports: list[ComponentExecutionReport] = []

        # --------------------------------------------------
        # 1. Execute independent recommendation providers.
        # --------------------------------------------------

        for component in self.REQUIRED_COMPONENTS:
            provider = self._providers.get(component)

            if provider is None:
                reports.append(
                    ComponentExecutionReport(
                        component=component,
                        status=ComponentExecutionStatus.DISABLED,
                        candidate_count=0,
                        duration_ms=0.0,
                    )
                )

                warnings.append(
                    f"{component.value} provider is not configured."
                )

                continue

            candidates, report = self._execute_provider(
                provider,
                context,
            )

            reports.append(report)

            if report.status == ComponentExecutionStatus.FAILED:
                warnings.append(
                    f"{component.value} provider failed."
                )

            elif report.status == ComponentExecutionStatus.EMPTY:
                warnings.append(
                    f"{component.value} provider returned no candidates."
                )

            if candidates:
                candidate_collections.append(candidates)

        reports_tuple = tuple(reports)

        total_discovered = sum(
            report.candidate_count
            for report in reports_tuple
        )

        # --------------------------------------------------
        # 2. Handle the no-candidate scenario.
        # --------------------------------------------------

        if not candidate_collections:
            duration_ms = (
                perf_counter() - started_at
            ) * 1000.0

            return HybridOrchestrationResult(
                request_id=request_id,
                user_id=context.user_id,
                ranked_candidates=(),
                filtering_results=(),
                component_reports=reports_tuple,
                total_candidates_discovered=0,
                total_candidates_after_deduplication=0,
                total_candidates_scored=0,
                total_candidates_accepted=0,
                total_candidates_returned=0,
                duration_ms=duration_ms,
                fallback_used=False,
                warnings=tuple(warnings),
            )

        # --------------------------------------------------
        # 3. Aggregate and deduplicate candidates.
        # --------------------------------------------------

        try:
            aggregation_result = (
                self._candidate_aggregator.aggregate(
                    tuple(candidate_collections)
                )
            )

        except CandidateAggregationError:
            logger.exception(
                "Hybrid candidate aggregation failed."
            )

            raise HybridOrchestrationError(
                "Candidate aggregation failed."
            )

        candidates = tuple(
            aggregation_result.candidates
        )

        candidates = self._add_missing_component_statuses(
            candidates,
            reports_tuple,
        )

        total_after_deduplication = len(candidates)

        if not candidates:
            duration_ms = (
                perf_counter() - started_at
            ) * 1000.0

            return HybridOrchestrationResult(
                request_id=request_id,
                user_id=context.user_id,
                ranked_candidates=(),
                filtering_results=(),
                component_reports=reports_tuple,
                total_candidates_discovered=total_discovered,
                total_candidates_after_deduplication=0,
                total_candidates_scored=0,
                total_candidates_accepted=0,
                total_candidates_returned=0,
                duration_ms=duration_ms,
                fallback_used=False,
                warnings=tuple(warnings),
            )

        # --------------------------------------------------
        # 4. Score candidates independently.
        # --------------------------------------------------

        score_results = {}
        scored_candidates: list[HybridCandidate] = []

        for candidate in candidates:
            try:
                score_result = self._scoring_pipeline.score(
                    candidate
                )

                if score_result.resource_id != candidate.resource_id:
                    raise HybridScoringError(
                        "Scoring result resource ID mismatch."
                    )

                score_results[candidate.resource_id] = score_result
                scored_candidates.append(candidate)

            except Exception as exc:
                logger.warning(
                    "Candidate scoring failed for %s: %s",
                    candidate.resource_id,
                    exc,
                )

                warnings.append(
                    f"Scoring failed for candidate "
                    f"{candidate.resource_id}."
                )

        candidates = tuple(scored_candidates)

        if not candidates:
            duration_ms = (
                perf_counter() - started_at
            ) * 1000.0

            return HybridOrchestrationResult(
                request_id=request_id,
                user_id=context.user_id,
                ranked_candidates=(),
                filtering_results=(),
                component_reports=reports_tuple,
                total_candidates_discovered=total_discovered,
                total_candidates_after_deduplication=(
                    total_after_deduplication
                ),
                total_candidates_scored=0,
                total_candidates_accepted=0,
                total_candidates_returned=0,
                duration_ms=duration_ms,
                fallback_used=False,
                warnings=tuple(warnings),
            )

        # --------------------------------------------------
        # 5. Resolve hard eligibility decisions.
        # --------------------------------------------------

        decisions = self._resolve_eligibility(
            candidates,
            context,
        )

        filtering_results = self._filtering_pipeline.execute(
            tuple(
                candidate.resource_id
                for candidate in candidates
            ),
            decisions,
        )

        # --------------------------------------------------
        # 6. Rank eligible candidates.
        # --------------------------------------------------

        ranking_response: HybridRankingResponse = (
            self._ranking_pipeline.execute(
                candidates=candidates,
                score_results=score_results,
                filtering_results=filtering_results,
                limit=limit,
            )
        )

        # --------------------------------------------------
        # 7. Build final diagnostics.
        # --------------------------------------------------

        successful_components = sum(
            1
            for report in reports_tuple
            if report.status == ComponentExecutionStatus.SUCCESS
        )

        fallback_used = (
            successful_components
            < len(self.REQUIRED_COMPONENTS)
            and ranking_response.total_returned > 0
        )

        duration_ms = (
            perf_counter() - started_at
        ) * 1000.0

        return HybridOrchestrationResult(
            request_id=request_id,
            user_id=context.user_id,
            ranked_candidates=ranking_response.ranked_candidates,
            filtering_results=ranking_response.filtering_results,
            component_reports=reports_tuple,
            total_candidates_discovered=total_discovered,
            total_candidates_after_deduplication=(
                total_after_deduplication
            ),
            total_candidates_scored=len(score_results),
            total_candidates_accepted=(
                ranking_response.total_accepted
            ),
            total_candidates_returned=(
                ranking_response.total_returned
            ),
            duration_ms=duration_ms,
            fallback_used=fallback_used,
            warnings=tuple(warnings),
        )