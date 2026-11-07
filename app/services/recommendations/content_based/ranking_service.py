from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from app.services.recommendations.content_based.candidate_models import (
    ContentBasedCandidate,
)


class ContentRankingError(ValueError):
    """Raised when content-based ranking inputs are invalid."""


@dataclass(frozen=True, slots=True)
class RankedContentRecommendation:

    candidate: ContentBasedCandidate

    rank_position: int

    @property
    def resource_id(self) -> UUID:

        return self.candidate.resource_id

    @property
    def score(self) -> float:

        return self.candidate.score

    @property
    def confidence(self) -> float:

        return self.candidate.confidence


class ContentBasedRankingService:
    """
    Deterministic ranking and duplicate resolution.

    Ordering:
    1. Content similarity score descending.
    2. Confidence descending.
    3. Resource quality descending.
    4. Resource UUID ascending.
    """

    DEFAULT_LIMIT = 10

    MAX_LIMIT = 50

    @staticmethod
    def _quality(candidate: ContentBasedCandidate) -> float:

        if candidate.quality_score is None:
            return 0.0

        return float(candidate.quality_score)

    @classmethod
    def _sort_key(cls, candidate: ContentBasedCandidate):

        return (
            -candidate.score,
            -candidate.confidence,
            -cls._quality(candidate),
            str(candidate.resource_id),
        )

    def rank(
        self,
        candidates: Iterable[ContentBasedCandidate],
        limit: int = DEFAULT_LIMIT,
    ) -> list[RankedContentRecommendation]:

        if isinstance(limit, bool) or not isinstance(limit, int):

            raise ContentRankingError(
                "Limit must be an integer."
            )

        if not 1 <= limit <= self.MAX_LIMIT:

            raise ContentRankingError(
                f"Limit must be between 1 and {self.MAX_LIMIT}."
            )

        if isinstance(candidates, (str, bytes)):

            raise TypeError(
                "Candidates must be an iterable of candidates."
            )

        try:
            iterator = iter(candidates)
        except TypeError:

            raise TypeError(
                "Candidates must be iterable."
            ) from None

        validated = []

        reference_resource_id = None

        for candidate in iterator:

            if not isinstance(candidate, ContentBasedCandidate):

                raise TypeError(
                    "Every item must be ContentBasedCandidate."
                )

            current_reference = (
                candidate.scoring_result.reference_resource_id
            )

            if reference_resource_id is None:

                reference_resource_id = current_reference

            elif current_reference != reference_resource_id:

                raise ContentRankingError(
                    "All candidates must use the same reference resource."
                )

            validated.append(candidate)

        ordered = sorted(
            validated,
            key=self._sort_key,
        )

        unique = []

        seen_resource_ids: set[UUID] = set()

        for candidate in ordered:

            if candidate.resource_id in seen_resource_ids:
                continue

            seen_resource_ids.add(
                candidate.resource_id
            )

            unique.append(candidate)

            if len(unique) >= limit:
                break

        return [
            RankedContentRecommendation(
                candidate=candidate,
                rank_position=index,
            )
            for index, candidate in enumerate(
                unique,
                start=1,
            )
        ]