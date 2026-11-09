from __future__ import annotations

from dataclasses import dataclass

from app.schemas.sparse_data import (
    ColdStartStrategy,
    SparseDataAssessment,
)


@dataclass(frozen=True)
class RecommendationStrategy:
    """
    Application-level guidance for candidate generation.

    These values are instructions for the recommendation
    orchestration layer. They do not modify Phase 15 scores
    automatically.
    """

    strategy: ColdStartStrategy

    exploration_ratio: float
    personalization_strength: float

    use_profile_preferences: bool
    use_behavioral_signals: bool
    use_explicit_feedback: bool

    include_general_candidates: bool
    require_candidate_diversity: bool

    preserve_hard_constraints: bool
    missing_evidence_is_neutral: bool


class ColdStartStrategyService:
    """
    Converts a sparse-data assessment into a recommendation
    strategy that can be consumed by the hybrid application layer.
    """

    def build_strategy(
        self,
        assessment: SparseDataAssessment,
    ) -> RecommendationStrategy:
        if assessment is None:
            raise ValueError(
                "sparse data assessment is required"
            )

        policy = assessment.policy

        return RecommendationStrategy(
            strategy=policy.strategy,
            exploration_ratio=policy.exploration_ratio,
            personalization_strength=(
                policy.personalization_strength
            ),
            use_profile_preferences=(
                policy.use_explicit_preferences
            ),
            use_behavioral_signals=(
                policy.use_behavioral_signals
            ),
            use_explicit_feedback=(
                policy.use_explicit_feedback
            ),
            include_general_candidates=(
                policy.use_general_fallback
            ),
            require_candidate_diversity=(
                assessment.is_sparse
            ),
            preserve_hard_constraints=(
                policy.preserve_hard_constraints
            ),
            missing_evidence_is_neutral=(
                policy.treat_missing_evidence_as_neutral
            ),
        )