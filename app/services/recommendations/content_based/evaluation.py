from __future__ import annotations

import math

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Hashable


class RecommendationEvaluationError(ValueError):
    """Raised when recommendation evaluation input is invalid."""


@dataclass(frozen=True, slots=True)
class RecommendationEvaluationMetrics:
    precision_at_k: float
    recall_at_k: float
    hit_rate_at_k: float
    reciprocal_rank: float
    ndcg_at_k: float
    k: int


@dataclass(frozen=True, slots=True)
class RecommendationEvaluationCase:
    recommended_ids: tuple[Hashable, ...]
    relevant_ids: frozenset[Hashable]


@dataclass(frozen=True, slots=True)
class AggregateEvaluationMetrics:
    query_count: int
    mean_precision_at_k: float
    mean_recall_at_k: float
    mean_hit_rate_at_k: float
    mean_reciprocal_rank: float
    mean_ndcg_at_k: float
    k: int


class RecommendationEvaluator:
    """
    Evaluate content-based recommendation ranking quality.

    Uses binary relevance:
    - Relevant resource: 1
    - Non-relevant resource: 0

    Duplicate recommendation IDs are removed while preserving order.
    """

    @staticmethod
    def _normalize_ids(
        values: Iterable[Hashable],
        field_name: str,
    ) -> tuple[Hashable, ...]:

        if isinstance(values, (str, bytes)):
            raise RecommendationEvaluationError(
                f"{field_name} must be an iterable of IDs."
            )

        if not isinstance(values, Iterable):
            raise RecommendationEvaluationError(
                f"{field_name} must be iterable."
            )

        normalized = []
        seen = set()

        try:
            for value in values:

                if value is None:
                    raise RecommendationEvaluationError(
                        f"{field_name} cannot contain None."
                    )

                try:
                    hash(value)
                except TypeError:
                    raise RecommendationEvaluationError(
                        f"{field_name} must contain hashable IDs."
                    ) from None

                if value not in seen:
                    seen.add(value)
                    normalized.append(value)

        except TypeError:
            raise RecommendationEvaluationError(
                f"{field_name} must be iterable."
            ) from None

        return tuple(normalized)

    @staticmethod
    def _validate_k(k: int) -> None:

        if (
            isinstance(k, bool)
            or not isinstance(k, int)
            or k <= 0
        ):
            raise RecommendationEvaluationError(
                "k must be a positive integer."
            )

    @staticmethod
    def _dcg(
        relevance: list[int],
    ) -> float:

        return sum(
            relevance[index]
            / math.log2(index + 2)
            for index in range(len(relevance))
        )

    def evaluate(
        self,
        recommended_ids: Iterable[Hashable],
        relevant_ids: Iterable[Hashable],
        k: int = 10,
    ) -> RecommendationEvaluationMetrics:
        """
        Evaluate one recommendation result.

        Precision denominator is always k.
        Recall denominator is the number of relevant resources.
        """

        self._validate_k(k)

        recommended = self._normalize_ids(
            recommended_ids,
            "recommended_ids",
        )

        relevant = set(
            self._normalize_ids(
                relevant_ids,
                "relevant_ids",
            )
        )

        top_k = recommended[:k]

        relevance = [
            1 if resource_id in relevant else 0
            for resource_id in top_k
        ]

        relevant_retrieved = sum(relevance)

        precision = relevant_retrieved / k

        recall = (
            relevant_retrieved / len(relevant)
            if relevant
            else 0.0
        )

        hit_rate = (
            1.0
            if relevant_retrieved > 0
            else 0.0
        )

        reciprocal_rank = 0.0

        for rank, is_relevant in enumerate(
            relevance,
            start=1,
        ):
            if is_relevant:
                reciprocal_rank = 1.0 / rank
                break

        dcg = self._dcg(relevance)

        ideal_relevance = [
            1
        ] * min(len(relevant), k)

        ideal_dcg = self._dcg(
            ideal_relevance
        )

        ndcg = (
            dcg / ideal_dcg
            if ideal_dcg > 0
            else 0.0
        )

        return RecommendationEvaluationMetrics(
            precision_at_k=precision,
            recall_at_k=recall,
            hit_rate_at_k=hit_rate,
            reciprocal_rank=reciprocal_rank,
            ndcg_at_k=ndcg,
            k=k,
        )

    def evaluate_batch(
        self,
        cases: Iterable[RecommendationEvaluationCase],
        k: int = 10,
    ) -> AggregateEvaluationMetrics:
        """
        Evaluate multiple recommendation queries.

        Returns macro-averaged metrics across queries.
        """

        self._validate_k(k)

        if isinstance(cases, (str, bytes)):
            raise RecommendationEvaluationError(
                "cases must be an iterable of evaluation cases."
            )

        try:
            cases = tuple(cases)
        except TypeError:
            raise RecommendationEvaluationError(
                "cases must be iterable."
            ) from None

        if not cases:
            raise RecommendationEvaluationError(
                "At least one evaluation case is required."
            )

        results = []

        for case in cases:

            if not isinstance(
                case,
                RecommendationEvaluationCase,
            ):
                raise RecommendationEvaluationError(
                    "Every case must be a "
                    "RecommendationEvaluationCase."
                )

            results.append(
                self.evaluate(
                    recommended_ids=case.recommended_ids,
                    relevant_ids=case.relevant_ids,
                    k=k,
                )
            )

        count = len(results)

        return AggregateEvaluationMetrics(
            query_count=count,
            mean_precision_at_k=sum(
                result.precision_at_k
                for result in results
            ) / count,
            mean_recall_at_k=sum(
                result.recall_at_k
                for result in results
            ) / count,
            mean_hit_rate_at_k=sum(
                result.hit_rate_at_k
                for result in results
            ) / count,
            mean_reciprocal_rank=sum(
                result.reciprocal_rank
                for result in results
            ) / count,
            mean_ndcg_at_k=sum(
                result.ndcg_at_k
                for result in results
            ) / count,
            k=k,
        )