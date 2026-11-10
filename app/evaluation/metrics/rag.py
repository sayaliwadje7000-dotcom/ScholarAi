def context_precision(relevance_judgments):
    if not relevance_judgments:
        return 0.0

    if not all(
        isinstance(value, bool)
        for value in relevance_judgments
    ):
        raise ValueError(
            "Relevance judgments must contain booleans."
        )

    return (
        sum(relevance_judgments)
        / len(relevance_judgments)
    )


def context_recall(retrieved_relevant, total_relevant):
    if retrieved_relevant < 0 or total_relevant < 0:
        raise ValueError("Counts cannot be negative.")

    if total_relevant == 0:
        return 0.0

    if retrieved_relevant > total_relevant:
        raise ValueError(
            "Retrieved relevant count cannot exceed total relevant."
        )

    return retrieved_relevant / total_relevant


def answer_relevance(relevance_scores):
    if not relevance_scores:
        return 0.0

    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or value not in (0, 1)
        for value in relevance_scores
    ):
        raise ValueError(
            "Relevance scores must contain only 0 or 1."
        )

    return sum(relevance_scores) / len(relevance_scores)


def faithfulness(supported_claims, unsupported_claims):
    if supported_claims < 0 or unsupported_claims < 0:
        raise ValueError("Claim counts cannot be negative.")

    total = supported_claims + unsupported_claims

    if total == 0:
        return 0.0

    return supported_claims / total


def answer_grounding(answer_claims, supported_claims):
    if not answer_claims:
        return 0.0

    if len(set(answer_claims)) != len(answer_claims):
        raise ValueError("Answer claims must be unique.")

    supported = set(supported_claims)
    total = len(answer_claims)

    return sum(
        claim in supported
        for claim in answer_claims
    ) / total