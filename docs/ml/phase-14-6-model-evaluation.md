# Phase 14.6 — Model Evaluation and Validation

## Objective

Evaluate the ScholarAI recommendation baseline model using held-out
validation data and compare its performance against a Dummy Classifier.

The evaluation process must not train or modify either model.

## Models

1. Logistic Regression recommendation baseline.
2. Dummy Classifier prior baseline.

Both models are evaluated using exactly the same validation candidates
and ground-truth labels.

## Classification metrics

- Accuracy
- Precision
- Recall
- F1-score
- Balanced accuracy
- Confusion matrix
- ROC-AUC
- PR-AUC
- Average precision

Classification predictions use a configurable probability threshold.

Default threshold: 0.50.

## Ranking metrics

Metrics are calculated independently for each user.

- Precision@K
- Recall@K
- NDCG@K

Default K values:

- 3
- 5
- 10

Precision@K uses K as its denominator, even if fewer than K candidates
are available.

Recall@K is averaged over users with at least one relevant candidate.
Users with no relevant candidates are excluded from recall averaging
and counted separately.

NDCG uses binary relevance labels.

Tied prediction scores are resolved deterministically by resource ID.

## Class imbalance

The evaluation report records:

- Relevant sample count.
- Non-relevant sample count.
- Relevant ratio.
- Non-relevant ratio.
- Majority-to-minority imbalance ratio.

Accuracy must not be interpreted independently when classes are
imbalanced.

## Baseline comparison

The trained model is compared with the Dummy Classifier using:

- Classification metrics.
- Average precision.
- PR-AUC.
- NDCG@K.

A learned model is considered to outperform the dummy baseline in this
report only when average precision is strictly higher and NDCG@K is
not lower for any configured K.

This is a comparison rule, not a universal production acceptance
threshold.

## Data integrity

- Evaluation uses held-out validation data.
- Validation labels are ground truth.
- User IDs are used only for grouping.
- Resource IDs are used only for deterministic tie-breaking.
- Identifiers are not model input features.
- The fitted feature transformer is not refitted.
- The evaluator does not access PostgreSQL.

## Limitations

The validation split is user-separated, not time-separated.

The current evaluation is not proof of future production performance.

Small datasets may produce unstable metrics.

Synthetic test data verifies implementation behavior, not real-world
recommendation quality.

## Phase 14.6 completion criteria

- Classification metrics implemented and tested.
- Probability metrics implemented and tested.
- Ranking metrics implemented and tested.
- User-level ranking aggregation implemented.
- Class imbalance reporting implemented.
- Dummy baseline comparison implemented.
- Evaluation report serialization implemented.
- Invalid input and prediction handling tested.
- Full ML test suite passes.