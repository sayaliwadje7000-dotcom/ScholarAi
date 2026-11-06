import math
import re
from uuid import UUID
from datetime import datetime, timezone
from typing import Iterable

from app.schemas.recommendations import (
    RecommendationScoreBreakdown,
    RecommendationScoringResult,
    RecommendationWeights,
)

from app.schemas.recommendation_context import (
    RecommendationContext,
)

from app.schemas.resource_metadata import (
    ResourceClassification,
)

from app.schemas.recommendation_rules import (
    RecommendationRuleConfiguration,
)

from app.services.recommendations.rule_evaluator import (
    RuleEvaluator,
)


class RecommendationScoringService:
    """
    Calculates deterministic, normalized recommendation scores.

    The service combines six independently calculated factors,
    then applies configured rule-based adjustments.
    """

    ALGORITHM_VERSION = "rule-based-v1"

    FRESHNESS_HALF_LIFE_DAYS = 365

    def __init__(
        self,
        weights: RecommendationWeights | None = None,
        rule_configuration: (
            RecommendationRuleConfiguration | None
        ) = None,
    ):
        self.weights = weights or RecommendationWeights()

        self.rule_configuration = (
            rule_configuration
            or RecommendationRuleConfiguration()
        )

        self.rule_evaluator = RuleEvaluator(
            self.rule_configuration
        )

    @staticmethod
    def _tokenize(value: str) -> set[str]:
        if not value:
            return set()

        return {
            token.casefold()
            for token in re.findall(
                r"[a-zA-Z0-9]+",
                value,
            )
            if len(token) > 1
        }

    @classmethod
    def _tokenize_many(
        cls,
        values: Iterable[str],
    ) -> set[str]:
        tokens = set()

        for value in values:
            if isinstance(value, str):
                tokens.update(cls._tokenize(value))

        return tokens

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    @classmethod
    def _jaccard_similarity(
        cls,
        first: set[str],
        second: set[str],
    ) -> float:
        if not first or not second:
            return 0.0

        intersection = first.intersection(second)
        union = first.union(second)

        return len(intersection) / len(union)

    def calculate_topic_relevance(
        self,
        resource: ResourceClassification,
        context: RecommendationContext,
    ) -> float:
        intent = context.intent
        learning = context.learning_context

        resource_tokens = self._tokenize_many(
            [
                resource.subject or "",
                *resource.topics,
                *resource.keywords,
                *resource.category_slugs,
            ]
        )

        query_tokens = self._tokenize(
            intent.query or ""
        )

        subject_tokens = self._tokenize_many(
            [
                intent.subject or "",
                *learning.preferred_subjects,
            ]
        )

        query_similarity = self._jaccard_similarity(
            resource_tokens,
            query_tokens,
        )

        subject_similarity = self._jaccard_similarity(
            resource_tokens,
            subject_tokens,
        )

        if query_tokens and subject_tokens:
            score = (
                0.65 * query_similarity
                + 0.35 * subject_similarity
            )

        elif query_tokens:
            score = query_similarity

        elif subject_tokens:
            score = subject_similarity

        else:
            score = 0.5

        return self._clamp(score)

    def calculate_learning_level(
        self,
        resource: ResourceClassification,
        context: RecommendationContext,
    ) -> float:
        requested_level = context.intent.difficulty_level

        if requested_level is None:
            return 0.5

        resource_level = resource.difficulty

        if resource_level is None:
            return 0.5

        levels = {
            "beginner": 0,
            "intermediate": 1,
            "advanced": 2,
        }

        requested = getattr(
            requested_level,
            "value",
            requested_level,
        )

        requested = str(requested).lower()
        resource_level = str(resource_level).lower()

        if requested not in levels:
            return 0.5

        if resource_level not in levels:
            return 0.5

        difference = abs(
            levels[requested] - levels[resource_level]
        )

        return {
            0: 1.0,
            1: 0.5,
            2: 0.0,
        }[difference]

    def calculate_prerequisite_compatibility(
        self,
        resource: ResourceClassification,
        context: RecommendationContext,
    ) -> float:
        """
        No prerequisite is treated as fully compatible.

        If prerequisites exist but there is insufficient evidence
        about the student's prerequisite knowledge, return 0.5.

        Interaction history alone is not treated as proof of mastery.
        """

        if not resource.prerequisites:
            return 1.0

        return 0.5

    def calculate_resource_quality(
        self,
        resource: ResourceClassification,
    ) -> float:
        if resource.quality_score is None:
            return 0.5

        return self._clamp(
            resource.quality_score / 5.0
        )

    def calculate_learning_objective_relevance(
        self,
        resource: ResourceClassification,
        context: RecommendationContext,
    ) -> float:
        objectives = self._tokenize_many(
            resource.learning_objectives
        )

        goals = self._tokenize_many(
            context.learning_context.learning_goals
        )

        if not objectives or not goals:
            return 0.5

        return self._clamp(
            self._jaccard_similarity(
                objectives,
                goals,
            )
        )

    def calculate_freshness(
        self,
        resource: ResourceClassification,
        reference_time: datetime | None = None,
    ) -> float:
        if resource.published_at is None:
            return 0.5

        reference_time = (
            reference_time
            or datetime.now(timezone.utc)
        )

        published_at = resource.published_at

        if published_at.tzinfo is None:
            published_at = published_at.replace(
                tzinfo=timezone.utc
            )

        if reference_time.tzinfo is None:
            reference_time = reference_time.replace(
                tzinfo=timezone.utc
            )

        age_days = max(
            0.0,
            (
                reference_time - published_at
            ).total_seconds() / 86400,
        )

        return self._clamp(
            math.pow(
                0.5,
                age_days / self.FRESHNESS_HALF_LIFE_DAYS,
            )
        )

    def calculate_breakdown(
        self,
        resource: ResourceClassification,
        context: RecommendationContext,
        reference_time: datetime | None = None,
    ) -> RecommendationScoreBreakdown:
        return RecommendationScoreBreakdown(
            topic_relevance=self.calculate_topic_relevance(
                resource,
                context,
            ),
            learning_level=self.calculate_learning_level(
                resource,
                context,
            ),
            prerequisite_compatibility=(
                self.calculate_prerequisite_compatibility(
                    resource,
                    context,
                )
            ),
            resource_quality=self.calculate_resource_quality(
                resource
            ),
            learning_objective=self.calculate_learning_objective_relevance(
                resource,
                context,
            ),
            freshness=self.calculate_freshness(
                resource,
                reference_time,
            ),
        )

    def calculate_base_score(
        self,
        breakdown: RecommendationScoreBreakdown,
    ) -> float:
        weighted_score = (
            breakdown.topic_relevance
            * float(self.weights.topic_relevance)
            +
            breakdown.learning_level
            * float(self.weights.learning_level)
            +
            breakdown.prerequisite_compatibility
            * float(self.weights.prerequisite_compatibility)
            +
            breakdown.resource_quality
            * float(self.weights.resource_quality)
            +
            breakdown.learning_objective
            * float(self.weights.learning_objective)
            +
            breakdown.freshness
            * float(self.weights.freshness)
        )

        return self._clamp(weighted_score)

    def score(
        self,
        resource: ResourceClassification,
        context: RecommendationContext,
        reference_time: datetime | None = None,
    ) -> RecommendationScoringResult | None:
        """
        Calculate the recommendation score.

        Returns None when the resource is rejected by eligibility
        or exclusion rules.
        """

        if not isinstance(
            resource,
            ResourceClassification,
        ):
            raise TypeError(
                "Expected ResourceClassification."
            )

        if not isinstance(
            context,
            RecommendationContext,
        ):
            raise TypeError(
                "Expected RecommendationContext."
            )

        breakdown = self.calculate_breakdown(
            resource,
            context,
            reference_time,
        )

        base_score = self.calculate_base_score(
            breakdown
        )

        rule_result = self.rule_evaluator.execute(
            resource=resource,
            context=context.learning_context,
            initial_score=base_score,
        )

        if not rule_result.eligible:
            return None

        return RecommendationScoringResult(
            resource_id=resource.resource_id,
            score=round(
                rule_result.adjusted_score,
                4,
            ),
            breakdown=breakdown,
            weights=self.weights,
            algorithm_version=self.ALGORITHM_VERSION,
        )
