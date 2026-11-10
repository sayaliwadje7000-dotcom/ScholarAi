from collections import Counter

from app.evaluation.metrics.validation import (
    validate_same_length,
    validate_non_empty,
)


def accuracy(y_true, y_pred):
    validate_same_length(y_true, y_pred)

    correct = sum(
        actual == predicted
        for actual, predicted in zip(y_true, y_pred)
    )

    return correct / len(y_true)


def _class_metrics(y_true, y_pred, label, zero_division=0):
    tp = sum(
        actual == label and predicted == label
        for actual, predicted in zip(y_true, y_pred)
    )

    fp = sum(
        actual != label and predicted == label
        for actual, predicted in zip(y_true, y_pred)
    )

    fn = sum(
        actual == label and predicted != label
        for actual, predicted in zip(y_true, y_pred)
    )

    precision = (
        tp / (tp + fp)
        if tp + fp
        else zero_division
    )

    recall = (
        tp / (tp + fn)
        if tp + fn
        else zero_division
    )

    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else zero_division
    )

    return precision, recall, f1


def precision_recall_f1(
    y_true,
    y_pred,
    average="binary",
    positive_label=1,
    zero_division=0,
):
    validate_same_length(y_true, y_pred)

    if average == "binary":
        precision, recall, f1 = _class_metrics(
            y_true,
            y_pred,
            positive_label,
            zero_division,
        )

        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

    if average not in ("macro", "weighted"):
        raise ValueError(
            "average must be binary, macro, or weighted."
        )

    labels = sorted(
        set(y_true) | set(y_pred),
        key=str,
    )

    metrics = {
        label: _class_metrics(
            y_true,
            y_pred,
            label,
            zero_division,
        )
        for label in labels
    }

    if average == "macro":
        return {
            metric: sum(values[index] for values in metrics.values())
            / len(metrics)
            for index, metric in enumerate(
                ["precision", "recall", "f1"]
            )
        }

    support = Counter(y_true)
    total = len(y_true)

    return {
        metric: sum(
            metrics[label][index] * support[label]
            for label in labels
        ) / total
        for index, metric in enumerate(
            ["precision", "recall", "f1"]
        )
    }


def balanced_accuracy(y_true, y_pred):
    validate_same_length(y_true, y_pred)

    labels = sorted(set(y_true), key=str)

    recalls = [
        _class_metrics(y_true, y_pred, label)[1]
        for label in labels
    ]

    return sum(recalls) / len(recalls)


def confusion_matrix(y_true, y_pred):
    validate_same_length(y_true, y_pred)

    labels = sorted(
        set(y_true) | set(y_pred),
        key=str,
    )

    matrix = {
        actual: {predicted: 0 for predicted in labels}
        for actual in labels
    }

    for actual, predicted in zip(y_true, y_pred):
        matrix[actual][predicted] += 1

    return matrix