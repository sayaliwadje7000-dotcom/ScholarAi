from math import log2
from typing import Iterable


def _validate_k(k: int) -> None:

    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise ValueError("k must be a positive integer.")


def precision_at_k(
    relevant_items: Iterable[str],
    recommended_items: Iterable[str],
    k: int,
) -> float:
    """
    Measures the proportion of relevant opportunities
    among the first k recommendations.
    """

    _validate_k(k)

    relevant = set(relevant_items)

    recommended = list(recommended_items)[:k]

    if not recommended:
        return 0.0

    relevant_count = sum(
        item in relevant
        for item in recommended
    )

    return relevant_count / len(recommended)


def recall_at_k(
    relevant_items: Iterable[str],
    recommended_items: Iterable[str],
    k: int,
) -> float:
    """
    Measures how many known relevant opportunities
    were retrieved in the first k recommendations.
    """

    _validate_k(k)

    relevant = set(relevant_items)

    if not relevant:
        return 0.0

    recommended = list(recommended_items)[:k]

    relevant_count = sum(
        item in relevant
        for item in recommended
    )

    return relevant_count / len(relevant)


def f1_score(
    precision: float,
    recall: float,
) -> float:
    """
    Harmonic mean of precision and recall.
    """

    if not 0 <= precision <= 1:
        raise ValueError("Precision must be between 0 and 1.")

    if not 0 <= recall <= 1:
        raise ValueError("Recall must be between 0 and 1.")

    if precision + recall == 0:
        return 0.0

    return (
        2 * precision * recall
        / (precision + recall)
    )


def dcg_at_k(
    relevance_scores: Iterable[float],
    k: int,
) -> float:
    """
    Discounted Cumulative Gain.

    Higher relevance near the beginning of the ranking
    contributes more to the score.
    """

    _validate_k(k)

    scores = list(relevance_scores)[:k]

    if any(score < 0 for score in scores):
        raise ValueError(
            "Relevance scores cannot be negative."
        )

    return sum(
        (2 ** score - 1) / log2(position + 1)
        for position, score in enumerate(
            scores,
            start=1,
        )
    )


def ndcg_at_k(
    relevance_scores: Iterable[float],
    k: int,
) -> float:
    """
    Normalized Discounted Cumulative Gain.

    Returns a value between 0 and 1.
    """

    _validate_k(k)

    scores = list(relevance_scores)[:k]

    if not scores:
        return 0.0

    actual_dcg = dcg_at_k(scores, k)

    ideal_scores = sorted(
        scores,
        reverse=True,
    )

    ideal_dcg = dcg_at_k(
        ideal_scores,
        k,
    )

    if ideal_dcg == 0:
        return 0.0

    return actual_dcg / ideal_dcg


def duplicate_rate(
    opportunity_ids: Iterable[str],
) -> float:
    """
    Measures the proportion of duplicate records
    in the returned opportunity collection.
    """

    items = list(opportunity_ids)

    if not items:
        return 0.0

    unique_count = len(set(items))

    return (
        len(items) - unique_count
    ) / len(items)


def expired_leakage_rate(
    opportunity_statuses: Iterable[str],
) -> float:
    """
    Measures the proportion of expired or cancelled
    opportunities in the returned recommendations.
    """

    statuses = list(opportunity_statuses)

    if not statuses:
        return 0.0

    invalid_count = sum(
        status.casefold() in {
            "expired",
            "cancelled",
            "closed",
        }
        for status in statuses
    )

    return invalid_count / len(statuses)


def eligibility_violation_rate(
    eligibility_statuses: Iterable[str],
) -> float:
    """
    Measures the proportion of explicitly ineligible
    opportunities in the returned recommendations.

    Unknown eligibility is not counted as a violation.
    """

    statuses = list(eligibility_statuses)

    if not statuses:
        return 0.0

    violations = sum(
        status.casefold() == "not_eligible"
        for status in statuses
    )

    return violations / len(statuses)


def provider_success_rate(
    successful_providers: int,
    requested_providers: int,
) -> float:
    """
    Measures provider availability for one discovery request.
    """

    if (
        isinstance(successful_providers, bool)
        or isinstance(requested_providers, bool)
        or not isinstance(successful_providers, int)
        or not isinstance(requested_providers, int)
    ):
        raise TypeError(
            "Provider counts must be integers."
        )

    if requested_providers < 0:
        raise ValueError(
            "Requested providers cannot be negative."
        )

    if successful_providers < 0:
        raise ValueError(
            "Successful providers cannot be negative."
        )

    if successful_providers > requested_providers:
        raise ValueError(
            "Successful providers cannot exceed requested providers."
        )

    if requested_providers == 0:
        return 0.0

    return (
        successful_providers / requested_providers
    )