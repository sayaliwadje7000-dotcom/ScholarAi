import math

from app.evaluation.metrics.validation import (
    validate_non_empty,
    validate_positive_k,
)


def precision_at_k(ranked_items, relevant_items, k):
    validate_non_empty(ranked_items, "ranked_items")
    validate_positive_k(k)

    hits = sum(
        item in relevant_items
        for item in ranked_items[:k]
    )

    return hits / k


def recall_at_k(ranked_items, relevant_items, k):
    validate_non_empty(ranked_items, "ranked_items")
    validate_positive_k(k)

    if not relevant_items:
        return None

    hits = sum(
        item in relevant_items
        for item in ranked_items[:k]
    )

    return hits / len(relevant_items)


def hit_rate_at_k(ranked_items, relevant_items, k):
    validate_positive_k(k)

    return float(
        any(item in relevant_items for item in ranked_items[:k])
    )


def reciprocal_rank(ranked_items, relevant_items):
    for index, item in enumerate(ranked_items, start=1):
        if item in relevant_items:
            return 1 / index

    return 0.0


def mean_reciprocal_rank(rankings, relevant_sets):
    validate_non_empty(rankings, "rankings")

    if len(rankings) != len(relevant_sets):
        raise ValueError("Input query counts must match.")

    return sum(
        reciprocal_rank(ranking, relevant)
        for ranking, relevant in zip(rankings, relevant_sets)
    ) / len(rankings)


def average_precision(ranked_items, relevant_items):
    if not relevant_items:
        return 0.0

    hits = 0
    precision_sum = 0.0

    for index, item in enumerate(ranked_items, start=1):
        if item in relevant_items:
            hits += 1
            precision_sum += hits / index

    return precision_sum / len(relevant_items)


def mean_average_precision(rankings, relevant_sets):
    validate_non_empty(rankings, "rankings")

    if len(rankings) != len(relevant_sets):
        raise ValueError("Input query counts must match.")

    valid_queries = [
        average_precision(ranking, relevant)
        for ranking, relevant in zip(rankings, relevant_sets)
        if relevant
    ]

    if not valid_queries:
        return 0.0

    return sum(valid_queries) / len(valid_queries)


def dcg_at_k(relevance, k):
    validate_positive_k(k)

    return sum(
        (2 ** value - 1) / math.log2(index + 1)
        for index, value in enumerate(relevance[:k], start=1)
    )


def ndcg_at_k(relevance, k):
    validate_positive_k(k)

    actual = dcg_at_k(relevance, k)

    ideal_relevance = sorted(
        relevance,
        reverse=True,
    )

    ideal = dcg_at_k(ideal_relevance, k)

    if ideal == 0:
        return 0.0

    return actual / ideal