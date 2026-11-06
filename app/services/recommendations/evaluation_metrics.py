from __future__ import annotations

from collections.abc import Sequence
from math import log2


def precision_at_k(
    recommended: Sequence[str],
    relevant: set[str],
    k: int,
) -> float:
    if k <= 0:
        raise ValueError("k must be greater than zero.")

    selected = list(recommended[:k])

    if not selected:
        return 0.0

    relevant_count = sum(
        item in relevant
        for item in selected
    )

    return relevant_count / len(selected)


def recall_at_k(
    recommended: Sequence[str],
    relevant: set[str],
    k: int,
) -> float:
    if k <= 0:
        raise ValueError("k must be greater than zero.")

    if not relevant:
        return 0.0

    selected = set(recommended[:k])

    return len(selected & relevant) / len(relevant)


def hit_rate_at_k(
    recommended: Sequence[str],
    relevant: set[str],
    k: int,
) -> float:
    if k <= 0:
        raise ValueError("k must be greater than zero.")

    return float(
        bool(set(recommended[:k]) & relevant)
    )


def reciprocal_rank(
    recommended: Sequence[str],
    relevant: set[str],
) -> float:
    for position, item in enumerate(recommended, start=1):
        if item in relevant:
            return 1.0 / position

    return 0.0


def ndcg_at_k(
    recommended: Sequence[str],
    relevant: set[str],
    k: int,
) -> float:
    if k <= 0:
        raise ValueError("k must be greater than zero.")

    selected = list(recommended[:k])

    if not selected or not relevant:
        return 0.0

    dcg = sum(
        1.0 / log2(position + 1)
        for position, item in enumerate(selected, start=1)
        if item in relevant
    )

    ideal_count = min(len(relevant), k)

    ideal_dcg = sum(
        1.0 / log2(position + 1)
        for position in range(1, ideal_count + 1)
    )

    return dcg / ideal_dcg if ideal_dcg else 0.0


def catalog_coverage(
    recommended: Sequence[str],
    catalog: set[str],
) -> float:
    if not catalog:
        return 0.0

    return len(set(recommended) & catalog) / len(catalog)


def intra_list_diversity(
    categories: dict[str, set[str]],
    recommended: Sequence[str],
) -> float:
    """
    Measures average category dissimilarity.

    Uses Jaccard similarity between resource category sets.
    """

    items = list(recommended)

    if len(items) < 2:
        return 0.0

    distances = []

    for index, first in enumerate(items):
        first_categories = categories.get(first, set())

        for second in items[index + 1:]:
            second_categories = categories.get(second, set())

            union = first_categories | second_categories

            if not union:
                similarity = 0.0
            else:
                similarity = (
                    len(first_categories & second_categories)
                    / len(union)
                )

            distances.append(1.0 - similarity)

    return sum(distances) / len(distances)