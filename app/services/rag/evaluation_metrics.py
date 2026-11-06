from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable


def normalize_text(text: str) -> list[str]:
    """
    Normalize text into lowercase alphanumeric tokens.
    """

    return re.findall(
        r"\b\w+\b",
        text.lower(),
    )


def precision_at_k(
    retrieved_ids: Iterable[str],
    expected_ids: Iterable[str],
    k: int,
) -> float:
    if k <= 0:
        raise ValueError("k must be greater than zero")

    retrieved = list(retrieved_ids)[:k]
    expected = set(expected_ids)

    if not retrieved:
        return 0.0

    relevant = sum(
        1
        for item in retrieved
        if item in expected
    )

    return relevant / k


def recall_at_k(
    retrieved_ids: Iterable[str],
    expected_ids: Iterable[str],
    k: int,
) -> float:
    if k <= 0:
        raise ValueError("k must be greater than zero")

    retrieved = set(list(retrieved_ids)[:k])
    expected = set(expected_ids)

    if not expected:
        return 1.0

    relevant = len(retrieved.intersection(expected))

    return relevant / len(expected)


def reciprocal_rank(
    retrieved_ids: Iterable[str],
    expected_ids: Iterable[str],
) -> float:
    expected = set(expected_ids)

    if not expected:
        return 1.0

    for rank, item in enumerate(retrieved_ids, start=1):
        if item in expected:
            return 1.0 / rank

    return 0.0


def token_f1(
    prediction: str,
    reference: str,
) -> float:
    """
    Token-overlap F1.

    This is a lexical similarity metric, not a
    semantic faithfulness measurement.
    """

    predicted_tokens = normalize_text(prediction)
    reference_tokens = normalize_text(reference)

    if not predicted_tokens and not reference_tokens:
        return 1.0

    if not predicted_tokens or not reference_tokens:
        return 0.0

    predicted_counts = Counter(predicted_tokens)
    reference_counts = Counter(reference_tokens)

    overlap = sum(
        (predicted_counts & reference_counts).values()
    )

    precision = overlap / len(predicted_tokens)
    recall = overlap / len(reference_tokens)

    if precision + recall == 0:
        return 0.0

    return (
        2 * precision * recall
    ) / (
        precision + recall
    )


def required_term_coverage(
    answer: str,
    required_terms: Iterable[str],
) -> float:
    terms = [
        term.strip().lower()
        for term in required_terms
        if term.strip()
    ]

    if not terms:
        return 1.0

    normalized_answer = answer.lower()

    matched = sum(
        1
        for term in terms
        if term in normalized_answer
    )

    return matched / len(terms)


def citation_precision_recall(
    actual_source_ids: Iterable[str],
    expected_source_ids: Iterable[str],
) -> tuple[float, float]:
    """
    Calculate citation precision and recall.
    """

    actual = set(actual_source_ids)
    expected = set(expected_source_ids)

    if not actual and not expected:
        return 1.0, 1.0

    if not actual:
        return 0.0, 0.0 if expected else 1.0

    if not expected:
        return 0.0, 1.0

    correct = len(actual.intersection(expected))

    precision = correct / len(actual)
    recall = correct / len(expected)

    return precision, recall


def mean(values: Iterable[float]) -> float:
    values = list(values)

    if not values:
        return 0.0

    return sum(values) / len(values)