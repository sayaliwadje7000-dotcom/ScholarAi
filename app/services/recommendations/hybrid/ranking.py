"""Deterministic ranking pipeline for hybrid recommendations."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping
from uuid import UUID

from app.services.recommendations.hybrid.contracts import (
    HybridCandidate,
    RecommendationComponent,
)
from app.services.recommendations.hybrid.filtering import (
    FilteringResult,
)
from app.services.recommendations.hybrid.scoring import (
    ComponentContribution,
    HybridScoreResult,
)


class HybridRankingError(ValueError):
    """Raised when hybrid ranking input or output is invalid."""


@dataclass(frozen=True)
class RankedHybridCandidate:
    """A candidate with its hybrid score and final rank."""

    resource: HybridCandidate
    score: HybridScoreResult
    rank: int

    def __post_init__(self) -> None:
        if not isinstance(self.resource, HybridCandidate):
            raise HybridRankingError(
                "resource must be a HybridCandidate."
            )

        if not isinstance(self.score, HybridScoreResult):
            raise HybridRankingError(
                "score must be a HybridScoreResult."
            )

        if self.resource.resource_id != self.score.resource_id:
            raise HybridRankingError(
                "Candidate and score resource IDs must match."
            )

        if (
            isinstance(self.rank, bool)
            or not isinstance(self.rank, int)
            or self.rank < 1
        ):
            raise HybridRankingError(
                "rank must be a positive integer."
            )


@dataclass(frozen=True)
class HybridRankingResponse:
    """Result of filtering and ranking hybrid candidates."""

    ranked_candidates: tuple[RankedHybridCandidate, ...]
    filtering_results: tuple[FilteringResult, ...]
    total_received: int
    total_accepted: int
    total_excluded: int
    total_returned: int

    def __post_init__(self) -> None:
        counts = {
            "total_received": self.total_received,
            "total_accepted": self.total_accepted,
            "total_excluded": self.total_excluded,
            "total_returned": self.total_returned,
        }

        for name, value in counts.items():
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise HybridRankingError(
                    f"{name} must be a non-negative integer."
                )

        if self.total_received != (
            self.total_accepted + self.total_excluded
        ):
            raise HybridRankingError(
                "Received count must equal accepted plus excluded candidates."
            )

        if self.total_returned != len(self.ranked_candidates):
            raise HybridRankingError(
                "Returned count must match the ranked candidate count."
            )

        if self.total_returned > self.total_accepted:
            raise HybridRankingError(
                "Returned candidates cannot exceed accepted candidates."
            )

        if len(self.filtering_results) != self.total_received:
            raise HybridRankingError(
                "Filtering result count must match total received."
            )

        ranks = [
            item.rank
            for item in self.ranked_candidates
        ]

        expected_ranks = list(
            range(1, self.total_returned + 1)
        )

        if ranks != expected_ranks:
            raise HybridRankingError(
                "Ranked candidates must have sequential ranks."
            )


class HybridRankingPipeline:
    """
    Applies deterministic ranking to eligible hybrid candidates.

    Responsibilities:
    - Validate candidate, score and filtering relationships.
    - Enforce hard filtering decisions.
    - Rank accepted candidates by hybrid score.
    - Apply deterministic tie-breaking.
    - Apply an optional result limit.
    - Return accurate counts before and after limiting.

    Eligibility decisions are authoritative. A high score cannot
    override a failed validity, eligibility or availability check.
    """

    def execute(
        self,
        candidates: tuple[HybridCandidate, ...],
        score_results: Mapping[UUID, HybridScoreResult],
        filtering_results: tuple[FilteringResult, ...],
        limit: int | None = None,
    ) -> HybridRankingResponse:
        """Validate, filter, rank and limit hybrid candidates."""

        if not isinstance(candidates, tuple):
            raise HybridRankingError(
                "candidates must be a tuple."
            )

        if not isinstance(score_results, Mapping):
            raise HybridRankingError(
                "score_results must be a mapping."
            )

        if not isinstance(filtering_results, tuple):
            raise HybridRankingError(
                "filtering_results must be a tuple."
            )

        if limit is not None:
            if (
                isinstance(limit, bool)
                or not isinstance(limit, int)
                or limit < 1
            ):
                raise HybridRankingError(
                    "limit must be a positive integer or None."
                )

        candidate_ids = [
            candidate.resource_id
            for candidate in candidates
            if isinstance(candidate, HybridCandidate)
        ]

        if len(candidate_ids) != len(candidates):
            raise HybridRankingError(
                "Every candidate must be a HybridCandidate."
            )

        if len(candidate_ids) != len(set(candidate_ids)):
            raise HybridRankingError(
                "Duplicate candidate resource IDs are not allowed."
            )

        score_ids = set(score_results.keys())

        if score_ids != set(candidate_ids):
            raise HybridRankingError(
                "Score results must match candidate resource IDs exactly."
            )

        filtering_ids: list[UUID] = []

        for result in filtering_results:
            if not isinstance(result, FilteringResult):
                raise HybridRankingError(
                    "Every filtering result must be a FilteringResult."
                )

            filtering_ids.append(result.resource_id)

        if len(filtering_ids) != len(set(filtering_ids)):
            raise HybridRankingError(
                "Duplicate filtering resource IDs are not allowed."
            )

        if set(filtering_ids) != set(candidate_ids):
            raise HybridRankingError(
                "Filtering results must match candidate resource IDs exactly."
            )

        filtering_by_id = {
            result.resource_id: result
            for result in filtering_results
        }

        # Validate every score, including scores belonging to candidates
        # that will subsequently be excluded by hard filtering.
        for resource_id, score in score_results.items():
            if not isinstance(score, HybridScoreResult):
                raise HybridRankingError(
                    f"Invalid score result for resource {resource_id}."
                )

            if score.resource_id != resource_id:
                raise HybridRankingError(
                    "Score mapping key and score resource ID must match."
                )

            if (
                isinstance(score.hybrid_score, bool)
                or not isinstance(score.hybrid_score, (int, float))
                or not isfinite(score.hybrid_score)
            ):
                raise HybridRankingError(
                    f"Invalid hybrid score for resource {resource_id}."
                )

            if not 0.0 <= score.hybrid_score <= 1.0:
                raise HybridRankingError(
                    f"Hybrid score for resource {resource_id} "
                    "must be between 0 and 1."
                )

        candidate_by_id = {
            candidate.resource_id: candidate
            for candidate in candidates
        }

        accepted_candidates: list[HybridCandidate] = []

        for candidate in candidates:
            filtering_result = filtering_by_id[
                candidate.resource_id
            ]

            if filtering_result.accepted:
                accepted_candidates.append(candidate)

        # Sort all accepted candidates before applying the limit.
        ranked_items = sorted(
            accepted_candidates,
            key=lambda candidate: self._sort_key(
                candidate,
                score_results[candidate.resource_id],
            ),
        )

        # Apply the limit only after filtering and ranking.
        if limit is not None:
            ranked_items = ranked_items[:limit]

        ranked_candidates = tuple(
            RankedHybridCandidate(
                resource=candidate,
                score=score_results[candidate.resource_id],
                rank=index,
            )
            for index, candidate in enumerate(
                ranked_items,
                start=1,
            )
        )

        total_received = len(candidates)

        total_accepted = len(accepted_candidates)

        total_excluded = (
            total_received - total_accepted
        )

        total_returned = len(ranked_candidates)

        return HybridRankingResponse(
            ranked_candidates=ranked_candidates,
            filtering_results=filtering_results,
            total_received=total_received,
            total_accepted=total_accepted,
            total_excluded=total_excluded,
            total_returned=total_returned,
        )

    @staticmethod
    def _component_score(
        score: HybridScoreResult,
        component: RecommendationComponent,
    ) -> float:
        """
        Return a component's normalized score for tie-breaking.

        Missing component contributions receive zero. This value is
        used only for deterministic tie-breaking, not hybrid scoring.
        """

        for contribution in score.contributions:
            if contribution.component == component:
                return contribution.normalized_score

        return 0.0

    def _sort_key(
        self,
        candidate: HybridCandidate,
        score: HybridScoreResult,
    ) -> tuple[float, float, float, str, str]:
        """
        Produce a deterministic ascending sort key.

        Priority:
        1. Higher hybrid score.
        2. Higher content-based normalized score.
        3. Higher rule-based normalized score.
        4. Alphabetical title, case-insensitive.
        5. Resource UUID.

        Negative numeric values allow ascending Python sorting to
        prioritize higher scores.
        """

        content_score = self._component_score(
            score,
            RecommendationComponent.CONTENT_BASED,
        )

        rule_score = self._component_score(
            score,
            RecommendationComponent.RULE_BASED,
        )

        return (
            -float(score.hybrid_score),
            -float(content_score),
            -float(rule_score),
            candidate.title.casefold(),
            str(candidate.resource_id),
        )