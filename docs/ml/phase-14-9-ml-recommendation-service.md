# Phase 14.9 — ML Recommendation Service

## 1. Objective

Implement a reusable inference service that uses the trained
recommendation model and fitted feature transformer from Phase 14.5.

The service converts candidate resource features into relevance
probabilities.

## 2. Architecture

The inference flow is:

1. Receive a user ID and candidate resource IDs.
2. Validate identifiers and candidate limits.
3. Extract inference-time features.
4. Convert feature rows into model-facing records.
5. Transform records using the fitted transformer.
6. Generate relevance probabilities.
7. Validate model outputs.
8. Construct structured prediction results.

## 3. Separation of responsibilities

The inference service does not:

- Train a model.
- Fit a transformer.
- Access the training dataset.
- Modify recommendation feedback.
- Replace rule-based recommendations.
- Replace content-based recommendations.

## 4. Model compatibility

A model and its transformer must originate from the same
training run.

The service records the model run ID with every prediction.

## 5. Prediction semantics

The model returns a probability between zero and one.

The configured relevance threshold converts that probability
into a binary relevance indicator.

The threshold does not represent a calibrated probability
unless calibration has been independently evaluated.

## 6. Error handling

The service distinguishes:

- Invalid input.
- Missing model.
- Incompatible model bundle.
- Feature extraction failure.
- Transformation failure.
- Prediction failure.
- Invalid model output.

## 7. Fallback boundary

This service does not silently manufacture ML scores when
the model is unavailable.

Fallback to rule-based or content-based recommendations
belongs to Phase 15 hybrid orchestration.

## 8. Privacy

User and resource IDs are used for internal association.
They are not passed as model features.

Inference logs must not contain raw personal identifiers
or sensitive feature values.

## 9. Limitations

The service is an inference component, not a complete
production recommendation platform.

Model calibration, monitoring, artifact lifecycle,
API integration and hybrid orchestration are separate work.

## 10. Acceptance criteria

- A valid model bundle produces predictions.
- The fitted transformer is never refitted during inference.
- Prediction count matches candidate count.
- Probabilities are finite and within [0, 1].
- Invalid identifiers are rejected.
- Model and transformer failures are surfaced.
- Prediction results preserve candidate ordering.
- Each result identifies its model run.