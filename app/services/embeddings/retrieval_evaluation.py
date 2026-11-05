from __future__ import annotations

from dataclasses import dataclass
from typing import Hashable, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class RetrievalMetrics:
    precision_at_k: float
    recall_at_k: float
    mean_reciprocal_rank: float
    relevant_retrieved: int
    retrieved_count: int
    relevant_count: int


@dataclass(frozen=True, slots=True)
class AggregateRetrievalMetrics:
    precision_at_k: float
    recall_at_k: float
    mean_reciprocal_rank: float
    query_count: int


def evaluate_retrieval(
    retrieved_ids: Sequence[Hashable],
    relevant_ids: Sequence[Hashable],
    k: int = 5,
) -> RetrievalMetrics:
    """
    Evaluate a single ranked retrieval result.

    Precision@K = relevant retrieved in top K / K
    Recall@K = relevant retrieved in top K / total relevant
    MRR = reciprocal rank of the first relevant result.
    """

    if isinstance(k, bool) or not isinstance(k, int) or k <= 0:
        raise ValueError("k must be a positive integer.")

    if len(set(retrieved_ids)) != len(retrieved_ids):
        raise ValueError("retrieved_ids must not contain duplicates.")

    relevant_set = set(relevant_ids)

    if not relevant_set:
        raise ValueError("relevant_ids must contain at least one relevant item.")

    ranked_results = list(retrieved_ids[:k])

    relevant_retrieved = sum(
        1 for item in ranked_results if item in relevant_set
    )

    precision = relevant_retrieved / k
    recall = relevant_retrieved / len(relevant_set)

    reciprocal_rank = 0.0

    for rank, item in enumerate(ranked_results, start=1):
        if item in relevant_set:
            reciprocal_rank = 1.0 / rank
            break

    return RetrievalMetrics(
        precision_at_k=precision,
        recall_at_k=recall,
        mean_reciprocal_rank=reciprocal_rank,
        relevant_retrieved=relevant_retrieved,
        retrieved_count=len(ranked_results),
        relevant_count=len(relevant_set),
    )


def evaluate_retrieval_batch(
    retrieved_by_query: Mapping[Hashable, Sequence[Hashable]],
    relevant_by_query: Mapping[Hashable, Sequence[Hashable]],
    k: int = 5,
) -> AggregateRetrievalMetrics:
    """
    Evaluate multiple queries using macro-averaged metrics.

    Every evaluated query must have at least one relevant item.
    """

    if not retrieved_by_query:
        raise ValueError("At least one retrieval query is required.")

    if set(retrieved_by_query) != set(relevant_by_query):
        raise ValueError(
            "Retrieved and relevant query IDs must match exactly."
        )

    results = [
        evaluate_retrieval(
            retrieved_ids=retrieved_by_query[query_id],
            relevant_ids=relevant_by_query[query_id],
            k=k,
        )
        for query_id in retrieved_by_query
    ]

    count = len(results)

    return AggregateRetrievalMetrics(
        precision_at_k=sum(
            result.precision_at_k for result in results
        ) / count,
        recall_at_k=sum(
            result.recall_at_k for result in results
        ) / count,
        mean_reciprocal_rank=sum(
            result.mean_reciprocal_rank for result in results
        ) / count,
        query_count=count,
    )