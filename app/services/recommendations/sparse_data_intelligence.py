from __future__ import annotations

from dataclasses import dataclass

from app.schemas.sparse_data import SparseDataAssessment

from app.services.recommendations.sparse_data_assessor import (
    SparseDataAssessor,
)

from app.services.recommendations.cold_start_strategy import (
    ColdStartStrategyService,
    RecommendationStrategy,
)

from app.services.recommendations.exploration_allocator import (
    CandidateAllocation,
    ExplorationAllocator,
)


@dataclass(frozen=True)
class SparseDataIntelligenceResult:
    assessment: SparseDataAssessment
    strategy: RecommendationStrategy
    allocation: CandidateAllocation


class SparseDataIntelligenceService:
    """
    Coordinates sparse-data assessment and cold-start strategy
    selection.

    It does not perform database access or candidate ranking.
    """

    def __init__(
        self,
        assessor: SparseDataAssessor | None = None,
        strategy_service: ColdStartStrategyService | None = None,
        allocator: ExplorationAllocator | None = None,
    ):
        self.assessor = assessor or SparseDataAssessor()

        self.strategy_service = (
            strategy_service or ColdStartStrategyService()
        )

        self.allocator = allocator or ExplorationAllocator()

    def evaluate(
        self,
        *,
        personalized_context,
        candidate_pool_size: int = 10,
    ) -> SparseDataIntelligenceResult:
        if isinstance(candidate_pool_size, bool):
            raise TypeError(
                "candidate_pool_size must be an integer"
            )

        if not isinstance(candidate_pool_size, int):
            raise TypeError(
                "candidate_pool_size must be an integer"
            )

        if candidate_pool_size < 0:
            raise ValueError(
                "candidate_pool_size cannot be negative"
            )

        assessment = self.assessor.assess(
            personalized_context
        )

        strategy = self.strategy_service.build_strategy(
            assessment
        )

        allocation = self.allocator.allocate(
            total_candidates=candidate_pool_size,
            exploration_ratio=strategy.exploration_ratio,
        )

        return SparseDataIntelligenceResult(
            assessment=assessment,
            strategy=strategy,
            allocation=allocation,
        )