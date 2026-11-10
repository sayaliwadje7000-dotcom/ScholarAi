import math


def precision_at_k(recommended, relevant, k):
    if k <= 0:
        raise ValueError("k must be positive")
    return len(set(recommended[:k]) & relevant) / k


def recall_at_k(recommended, relevant, k):
    if k <= 0:
        raise ValueError("k must be positive")
    if not relevant:
        return 0.0
    return len(set(recommended[:k]) & relevant) / len(relevant)


def hit_rate_at_k(recommended, relevant, k):
    if k <= 0:
        raise ValueError("k must be positive")
    return float(bool(set(recommended[:k]) & relevant))


def reciprocal_rank(recommended, relevant):
    for index, item in enumerate(recommended, start=1):
        if item in relevant:
            return 1.0 / index
    return 0.0


def ndcg_at_k(recommended, relevant, k):
    if k <= 0:
        raise ValueError("k must be positive")

    dcg = sum(
        1.0 / math.log2(index + 2)
        for index, item in enumerate(recommended[:k])
        if item in relevant
    )

    ideal_count = min(len(relevant), k)
    if ideal_count == 0:
        return 0.0

    idcg = sum(
        1.0 / math.log2(index + 2)
        for index in range(ideal_count)
    )
    return dcg / idcg


def personalization_alignment(recommended, item_tags, preference_tags):
    if not recommended or not preference_tags:
        return 0.0

    scores = [
        len(set(item_tags.get(item, [])) & preference_tags)
        / len(preference_tags)
        for item in recommended
    ]
    return sum(scores) / len(scores)


def discovery_relevance(recommended, discovery_items, relevant_items):
    discovered = [
        item for item in recommended if item in discovery_items
    ]
    if not discovered:
        return 0.0
    return sum(
        item in relevant_items for item in discovered
    ) / len(discovered)


def intra_list_diversity(recommended, item_tags):
    if len(recommended) < 2:
        return 0.0

    distances = []

    for index, first in enumerate(recommended):
        first_tags = set(item_tags.get(first, []))

        for second in recommended[index + 1:]:
            second_tags = set(item_tags.get(second, []))
            union = first_tags | second_tags

            if not union:
                distances.append(0.0)
            else:
                similarity = len(first_tags & second_tags) / len(union)
                distances.append(1.0 - similarity)

    return sum(distances) / len(distances)


def novelty(recommended, item_popularity):
    if not recommended:
        return 0.0

    scores = []

    for item in recommended:
        popularity = min(
            max(item_popularity.get(item, 0.0), 0.0),
            1.0,
        )
        scores.append(1.0 - popularity)

    return sum(scores) / len(scores)


def serendipity(recommended, expected_items, relevant_items):
    if not recommended:
        return 0.0

    unexpected_relevant = [
        item for item in recommended
        if item not in expected_items and item in relevant_items
    ]

    return len(unexpected_relevant) / len(recommended)
