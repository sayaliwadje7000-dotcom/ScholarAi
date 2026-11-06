from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from app.schemas.recommendations import (
    InteractionType,
    RecommendationRequest,
    RecommendationScoringResult,
)

from app.schemas.resource_metadata import ResourceClassification


class RecommendationFilteringService:
    """
    Applies deterministic filtering to scored recommendation candidates.

    Filtering does not modify recommendation scores.
    """

    COMPLETION_INTERACTION = InteractionType.COMPLETE.value

    @staticmethod
    def _normalize(value: object) -> str:
        if value is None:
            return ""

        return str(
            getattr(value, "value", value)
        ).strip().casefold()

    @staticmethod
    def _resource_id(resource: ResourceClassification) -> UUID:
        return UUID(str(resource.resource_id))

    def _completed_resource_ids(
        self,
        interactions: Iterable[object],
    ) -> set[UUID]:
        completed: set[UUID] = set()

        for interaction in interactions:
            interaction_type = self._normalize(
                getattr(interaction, "interaction_type", None)
            )

            if interaction_type != self.COMPLETION_INTERACTION:
                continue

            resource_id = getattr(
                interaction,
                "resource_id",
                None,
            )

            try:
                completed.add(UUID(str(resource_id)))
            except (TypeError, ValueError, AttributeError):
                continue

        return completed

    def matches_request(
        self,
        resource: ResourceClassification,
        request: RecommendationRequest,
    ) -> bool:
        """
        Determine whether a resource satisfies explicit request filters.

        Missing resource metadata does not satisfy an explicit filter.
        """

        if not resource.is_active:
            return False

        if request.resource_types:
            allowed_types = {
                self._normalize(resource_type)
                for resource_type in request.resource_types
            }

            if self._normalize(resource.resource_type) not in allowed_types:
                return False

        if request.language:
            if self._normalize(resource.language) != self._normalize(
                request.language
            ):
                return False

        if request.subject:
            if self._normalize(resource.subject) != self._normalize(
                request.subject
            ):
                return False

        if request.difficulty_level:
            if self._normalize(resource.difficulty) != self._normalize(
                request.difficulty_level
            ):
                return False

        return True

    def filter(
        self,
        candidates: Iterable[
            tuple[
                ResourceClassification,
                RecommendationScoringResult,
            ]
        ],
        request: RecommendationRequest,
        interactions: Iterable[object] = (),
    ) -> list[
        tuple[
            ResourceClassification,
            RecommendationScoringResult,
        ]
    ]:
        """
        Filter scored candidates without changing their scores.

        Duplicate resource IDs are intentionally retained here.
        Ranking resolves duplicates by keeping the highest-scoring
        eligible occurrence.
        """

        if not isinstance(request, RecommendationRequest):
            raise TypeError(
                "Expected RecommendationRequest."
            )

        completed_ids = (
            self._completed_resource_ids(interactions)
            if request.exclude_completed
            else set()
        )

        filtered = []

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

            resource_id = self._resource_id(resource)

            if resource_id != scoring_result.resource_id:
                raise ValueError(
                    "Resource ID does not match scoring result."
                )

            if not self.matches_request(resource, request):
                continue

            if resource_id in completed_ids:
                continue

            filtered.append(
                (resource, scoring_result)
            )

        return filtered