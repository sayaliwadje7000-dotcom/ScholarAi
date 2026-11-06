from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from app.schemas.recommendations import (
    RecommendationScoringResult,
)

from app.schemas.resource_metadata import (
    ResourceClassification,
)


@dataclass(frozen=True, slots=True)
class RankedRecommendation:
    """
    Immutable ranked recommendation result.

    Explanations are added in Phase 10.8.
    """

    resource: ResourceClassification
    scoring_result: RecommendationScoringResult
    rank_position: int

    @property
    def resource_id(self) -> UUID:
        return self.scoring_result.resource_id

    @property
    def score(self):
        return self.scoring_result.score

    @property
    def algorithm_version(self) -> str:
        return self.scoring_result.algorithm_version


class RecommendationRankingService:
    """
    Deterministic recommendation ranking.

    Ordering:
        1. Higher score first.
        2. Higher resource quality first.
        3. Resource UUID ascending.

    Duplicate resource IDs are resolved after sorting.
    """

    @staticmethod
    def _quality(resource: ResourceClassification) -> float:
        if resource.quality_score is None:
            return -1.0

        return float(resource.quality_score)

    @staticmethod
    def _sort_key(
        candidate: tuple[
            ResourceClassification,
            RecommendationScoringResult,
        ],
    ) -> tuple[float, float, str]:
        resource, scoring_result = candidate

        return (
            -float(scoring_result.score),
            -RecommendationRankingService._quality(resource),
            str(scoring_result.resource_id),
        )

    def rank(
        self,
        candidates: Iterable[
            tuple[
                ResourceClassification,
                RecommendationScoringResult,
            ]
        ],
        limit: int = 10,
    ) -> list[RankedRecommendation]:
        """
        Rank scored resources.

        The limit is applied after duplicate removal.
        """

        if isinstance(limit, bool) or not isinstance(limit, int):
            raise TypeError(
                "Limit must be an integer."
            )

        if not 1 <= limit <= 50:
            raise ValueError(
                "Limit must be between 1 and 50."
            )

        validated = []

        for resource, scoring_result in candidates:
            if not isinstance(resource, ResourceClassification):
                raise TypeError(
                    "Expected ResourceClassification."
                )

            if not isinstance(
                scoring_result,
                RecommendationScoringResult,
            ):
                raise TypeError(
                    "Expected RecommendationScoringResult."
                )

            resource_id = UUID(str(resource.resource_id))

            if resource_id != scoring_result.resource_id:
                raise ValueError(
                    "Resource ID does not match scoring result."
                )

            validated.append(
                (resource, scoring_result)
            )

        ordered = sorted(
            validated,
            key=self._sort_key,
        )

        unique = []
        seen_resource_ids: set[UUID] = set()

        for resource, scoring_result in ordered:
            resource_id = scoring_result.resource_id

            if resource_id in seen_resource_ids:
                continue

            seen_resource_ids.add(resource_id)

            unique.append(
                (resource, scoring_result)
            )

            if len(unique) >= limit:
                break

        return [
            RankedRecommendation(
                resource=resource,
                scoring_result=scoring_result,
                rank_position=index,
            )
            for index, (resource, scoring_result) in enumerate(
                unique,
                start=1,
            )
        ]