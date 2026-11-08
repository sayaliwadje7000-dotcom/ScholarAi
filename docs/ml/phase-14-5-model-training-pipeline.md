# Phase 14.5 — Model Training Pipeline

## Objective

Build a reproducible training pipeline for ScholarAI's
machine-learning recommendation system.

## Architecture

The training pipeline consumes:

1. RecommendationFeatureRow objects.
2. RecommendationTrainingExample objects.

It produces:

1. A trained Logistic Regression model.
2. A trained Dummy Classifier baseline.
3. A fitted feature transformer.
4. Training metadata.
5. A held-out validation dataset.
6. A persistable model artifact.

## Dataset Validation

The pipeline validates:

- Non-empty feature datasets.
- Non-empty label datasets.
- Unique user-resource feature keys.
- Unique user-resource label keys.
- Exact feature-label key alignment.
- Binary relevance labels.
- Both relevance classes.

## Dataset Splitting

The pipeline uses GroupShuffleSplit.

All examples belonging to the same user remain in
one partition.

The default validation proportion is 20%.

The split is deterministic through a fixed random state.

Both partitions must contain both relevance classes.

## Feature Transformation

The feature transformer is fitted exclusively on
training data.

Validation data is transformed using the fitted
training transformer.

This prevents validation data from influencing
the learned vocabulary, encoding or scaling statistics.

## Model Training

The pipeline trains:

- Logistic Regression.
- Dummy Classifier using prior probabilities.

Label confidence is passed as sample weights
to Logistic Regression.

## Model Artifact

Artifacts contain:

- Model object.
- Dummy baseline.
- Fitted feature transformer.
- Model version.
- Feature schema version.
- Training configuration.
- Training statistics.
- Feature names.
- Run identifier.

Artifacts use joblib serialization and atomic replacement.

Only trusted artifacts must be loaded.

## Privacy

User and resource UUIDs are used for grouping and
evaluation metadata.

They are not passed as model features.

## Database Integration

No database queries or schema migrations are
introduced in this phase.

Database-backed dataset construction remains a
separate integration task.

## Implementation

- training/training_config.py
- training/training_pipeline.py
- training/artifact_store.py

## Tests

- test_training_config.py
- test_training_pipeline.py
- test_artifact_store.py

## Next Phase

Phase 14.6 — Model Evaluation and Validation.