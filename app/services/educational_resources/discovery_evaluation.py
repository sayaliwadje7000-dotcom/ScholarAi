from __future__ import annotations

import math

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class RankingMetrics:
    """
    Evaluation metrics for ranked educational resources.
    """

    precision_at_k: float
    recall_at_k: float
    reciprocal_rank: float
    ndcg_at_k: float
    k: int

    def __post_init__(self) -> None:
        metrics = (
            self.precision_at_k,
            self.recall_at_k,
            self.reciprocal_rank,
            self.ndcg_at_k,
        )

        for value in metrics:
            if not math.isfinite(value):
                raise ValueError(
                    "Evaluation metrics must be finite."
                )

            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    "Evaluation metrics must be between 0 and 1."
                )

        if isinstance(self.k, bool) or self.k <= 0:
            raise ValueError(
                "k must be a positive integer."
            )

    def to_dict(self) -> dict:
        return {
            "precision_at_k": self.precision_at_k,
            "recall_at_k": self.recall_at_k,
            "reciprocal_rank": self.reciprocal_rank,
            "ndcg_at_k": self.ndcg_at_k,
            "k": self.k,
        }


class DiscoveryEvaluator:
    """
    Evaluates the relevance of ranked educational resources.

    Relevance judgments are supplied externally.

    A relevance score greater than zero means that a resource
    is considered relevant.

    Higher relevance scores represent stronger relevance.
    """

    @staticmethod
    def _validate_identifier(value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                "Resource identifiers must be non-empty strings."
            )

    @staticmethod
    def _validate_k(k: int) -> None:
        if isinstance(k, bool) or not isinstance(k, int) or k <= 0:
            raise ValueError(
                "k must be a positive integer."
            )

    @staticmethod
    def _validate_relevance(
        relevance: Mapping[str, int | float],
    ) -> None:
        if not isinstance(relevance, Mapping):
            raise TypeError(
                "relevance must be a mapping."
            )

        for resource_id, score in relevance.items():
            DiscoveryEvaluator._validate_identifier(
                resource_id
            )

            if isinstance(score, bool) or not isinstance(
                score,
                (int, float),
            ):
                raise TypeError(
                    "Relevance scores must be numeric."
                )

            if not math.isfinite(score) or score < 0:
                raise ValueError(
                    "Relevance scores must be finite and non-negative."
                )

    @staticmethod
    def _normalize_ranking(
        ranked_resource_ids: Sequence[str],
    ) -> list[str]:
        if isinstance(
            ranked_resource_ids,
            (str, bytes),
        ) or not isinstance(
            ranked_resource_ids,
            Sequence,
        ):
            raise TypeError(
                "ranked_resource_ids must be a sequence."
            )

        normalized = []
        seen = set()

        for resource_id in ranked_resource_ids:
            DiscoveryEvaluator._validate_identifier(
                resource_id
            )

            if resource_id not in seen:
                normalized.append(resource_id)
                seen.add(resource_id)

        return normalized

    @staticmethod
    def precision_at_k(
        ranked_resource_ids: Sequence[str],
        relevance: Mapping[str, int | float],
        k: int = 10,
    ) -> float:
        """
        Calculate Precision@K.

        The denominator is always K.
        """

        DiscoveryEvaluator._validate_k(k)
        DiscoveryEvaluator._validate_relevance(relevance)

        ranking = DiscoveryEvaluator._normalize_ranking(
            ranked_resource_ids
        )

        top_k = ranking[:k]

        relevant_count = sum(
            1
            for resource_id in top_k
            if relevance.get(resource_id, 0) > 0
        )

        return relevant_count / k

    @staticmethod
    def recall_at_k(
        ranked_resource_ids: Sequence[str],
        relevance: Mapping[str, int | float],
        k: int = 10,
    ) -> float:
        """
        Calculate Recall@K.
        """

        DiscoveryEvaluator._validate_k(k)
        DiscoveryEvaluator._validate_relevance(relevance)

        ranking = DiscoveryEvaluator._normalize_ranking(
            ranked_resource_ids
        )

        total_relevant = sum(
            1
            for score in relevance.values()
            if score > 0
        )

        if total_relevant == 0:
            return 0.0

        retrieved_relevant = sum(
            1
            for resource_id in ranking[:k]
            if relevance.get(resource_id, 0) > 0
        )

        return retrieved_relevant / total_relevant

    @staticmethod
    def reciprocal_rank(
        ranked_resource_ids: Sequence[str],
        relevance: Mapping[str, int | float],
        k: int = 10,
    ) -> float:
        """
        Calculate Reciprocal Rank at K.
        """

        DiscoveryEvaluator._validate_k(k)
        DiscoveryEvaluator._validate_relevance(relevance)

        ranking = DiscoveryEvaluator._normalize_ranking(
            ranked_resource_ids
        )

        for index, resource_id in enumerate(
            ranking[:k],
            start=1,
        ):
            if relevance.get(resource_id, 0) > 0:
                return 1.0 / index

        return 0.0

    @staticmethod
    def ndcg_at_k(
        ranked_resource_ids: Sequence[str],
        relevance: Mapping[str, int | float],
        k: int = 10,
    ) -> float:
        """
        Calculate Normalized Discounted Cumulative Gain.

        Uses graded relevance judgments.
        """

        DiscoveryEvaluator._validate_k(k)
        DiscoveryEvaluator._validate_relevance(relevance)

        ranking = DiscoveryEvaluator._normalize_ranking(
            ranked_resource_ids
        )

        def dcg(scores: Sequence[int | float]) -> float:
            total = 0.0

            for index, score in enumerate(
                scores,
                start=1,
            ):
                gain = (2 ** score) - 1

                discount = math.log2(index + 1)

                total += gain / discount

            return total

        actual_scores = [
            relevance.get(resource_id, 0)
            for resource_id in ranking[:k]
        ]

        ideal_scores = sorted(
            relevance.values(),
            reverse=True,
        )[:k]

        actual_dcg = dcg(actual_scores)
        ideal_dcg = dcg(ideal_scores)

        if ideal_dcg == 0:
            return 0.0

        return actual_dcg / ideal_dcg

    @classmethod
    def evaluate(
        cls,
        ranked_resource_ids: Sequence[str],
        relevance: Mapping[str, int | float],
        k: int = 10,
    ) -> RankingMetrics:
        """
        Calculate all ranking metrics.
        """

        return RankingMetrics(
            precision_at_k=cls.precision_at_k(
                ranked_resource_ids,
                relevance,
                k,
            ),
            recall_at_k=cls.recall_at_k(
                ranked_resource_ids,
                relevance,
                k,
            ),
            reciprocal_rank=cls.reciprocal_rank(
                ranked_resource_ids,
                relevance,
                k,
            ),
            ndcg_at_k=cls.ndcg_at_k(
                ranked_resource_ids,
                relevance,
                k,
            ),
            k=k,
        )