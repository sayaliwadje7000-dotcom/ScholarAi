from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CandidateAllocation:
    exploration_count: int
    personalized_count: int
    total_count: int


class ExplorationAllocator:
    """
    Calculates the candidate allocation between exploration
    and personalization.

    The returned counts are targets for candidate generation.
    They do not imply that a candidate exists or is relevant.
    """

    def allocate(
        self,
        *,
        total_candidates: int,
        exploration_ratio: float,
    ) -> CandidateAllocation:
        if isinstance(total_candidates, bool):
            raise TypeError(
                "total_candidates must be an integer"
            )

        if not isinstance(total_candidates, int):
            raise TypeError(
                "total_candidates must be an integer"
            )

        if total_candidates < 0:
            raise ValueError(
                "total_candidates cannot be negative"
            )

        if isinstance(exploration_ratio, bool):
            raise TypeError(
                "exploration_ratio must be numeric"
            )

        try:
            ratio = float(exploration_ratio)
        except (TypeError, ValueError, OverflowError):
            raise TypeError(
                "exploration_ratio must be numeric"
            )

        if not 0.0 <= ratio <= 1.0:
            raise ValueError(
                "exploration_ratio must be between 0 and 1"
            )

        exploration_count = round(
            total_candidates * ratio
        )

        exploration_count = min(
            total_candidates,
            max(0, exploration_count),
        )

        personalized_count = (
            total_candidates - exploration_count
        )

        return CandidateAllocation(
            exploration_count=exploration_count,
            personalized_count=personalized_count,
            total_count=total_candidates,
        )