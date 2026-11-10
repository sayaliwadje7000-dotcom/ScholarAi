import re
from collections import Counter


def normalize_text(text):
    if not isinstance(text, str):
        raise ValueError("Text must be a string.")

    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)

    return " ".join(text.split())


def exact_match(prediction, reference):
    return float(
        normalize_text(prediction)
        == normalize_text(reference)
    )


def token_precision(prediction, reference):
    predicted_tokens = normalize_text(prediction).split()
    reference_tokens = normalize_text(reference).split()

    if not predicted_tokens:
        return 0.0

    overlap = sum(
        (Counter(predicted_tokens) & Counter(reference_tokens)).values()
    )

    return overlap / len(predicted_tokens)


def token_recall(prediction, reference):
    predicted_tokens = normalize_text(prediction).split()
    reference_tokens = normalize_text(reference).split()

    if not reference_tokens:
        return 0.0

    overlap = sum(
        (Counter(predicted_tokens) & Counter(reference_tokens)).values()
    )

    return overlap / len(reference_tokens)


def token_f1(prediction, reference):
    precision = token_precision(prediction, reference)
    recall = token_recall(prediction, reference)

    if precision + recall == 0:
        return 0.0

    return (
        2 * precision * recall
        / (precision + recall)
    )