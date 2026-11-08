# Phase 14.7 — Experiment Tracking and Reproducibility

## Objective

Implement persistent experiment tracking for the ScholarAI
recommendation machine-learning pipeline.

The objective is to make training experiments traceable,
comparable and reproducible.

## Architecture

The experiment tracking subsystem contains:

- ExperimentTrackingConfig
- ExperimentRecord
- RecommendationExperimentTracker
- ExperimentComparison
- compare_experiments

## Responsibilities

### Experiment configuration

Defines:

- Metadata storage directory
- Experiment schema version
- Environment metadata collection
- Dataset fingerprint collection
- Overwrite policy

### Experiment record

Stores:

- Run ID
- Training timestamp
- Experiment recording timestamp
- Model name
- Training configuration
- Training statistics
- Validation statistics
- Class distributions
- Feature names
- Evaluation report
- Environment information
- Dataset fingerprint
- Tags
- Optional artifact reference

### Experiment tracker

Provides:

- Experiment registration
- JSON persistence
- Duplicate run protection
- Atomic metadata writes
- Experiment retrieval
- Experiment listing
- Metadata validation

### Experiment comparison

Extracts:

- Accuracy
- Precision
- Recall
- F1 score
- ROC-AUC
- Average precision
- Ranking metrics

## Storage

Experiment metadata is stored under:

artifacts/recommendation_experiments/

Each experiment receives a separate JSON file.

Example:

artifacts/
    recommendation_experiments/
        scholarai-ml-run-001.json
        scholarai-ml-run-002.json

## Reproducibility

The tracker records the training configuration,
including the random seed and validation split settings.

It also records software environment information
and a fingerprint of the validation dataset's labels,
matrix shape and feature names.

The fingerprint excludes user and resource identifiers.

## Privacy

The experiment tracker does not persist:

- User IDs
- Resource IDs
- Raw training records
- Raw validation feature matrices
- User interaction histories

Experiment tags must not contain personal information.

## Model artifacts

The experiment tracker stores metadata, not model weights.

Model serialization remains the responsibility
of the Phase 14.5 model artifact store.

An artifact reference can be attached to an experiment
to associate its metadata with a saved model.

## Limitations

A dataset fingerprint is not a complete dataset archive.

Exact reproduction also requires access to the original
authorized data, feature extraction logic, code version,
model artifact, and compatible software environment.

Package versions and random seeds improve reproducibility
but do not guarantee bit-for-bit identical results across
all hardware and software environments.

## Verification

Run:

python -m pytest tests/services/recommendations/ml/experiments -v

Then:

python -m pytest -v