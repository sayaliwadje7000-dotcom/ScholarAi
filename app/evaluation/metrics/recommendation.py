import math


def catalog_coverage(recommendation_lists, catalog):
    if not catalog:
        return 0.0

    recommended = {
        item
        for recommendations in recommendation_lists
        for item in recommendations
    }

    return len(recommended & set(catalog)) / len(catalog)


def intra_list_diversity(items, similarity_function):
    if len(items) < 2:
        return 0.0

    if len(set(items)) != len(items):
        raise ValueError("Recommendation items must be unique.")

    total_distance = 0.0
    pairs = 0

    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            similarity = similarity_function(
                items[i],
                items[j],
            )

            if not 0 <= similarity <= 1:
                raise ValueError(
                    "Similarity must be between 0 and 1."
                )

            total_distance += 1 - similarity
            pairs += 1

    return total_distance / pairs


def novelty(items, popularity, total_interactions):
    if total_interactions < 0:
        raise ValueError("Interaction count cannot be negative.")

    if not items:
        return 0.0

    if total_interactions == 0:
        return 0.0

    total = 0.0

    for item in items:
        count = popularity.get(item, 0)

        if count < 0 or count > total_interactions:
            raise ValueError("Invalid popularity count.")

        probability = (
            count + 1
        ) / (
            total_interactions + 1
        )

        total += -math.log2(probability)

    return total / len(items)