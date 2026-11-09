# Phase 14.10 — ML Recommendation API Integration

## Objective

Expose the Phase 14.9 machine-learning recommendation service
through a versioned FastAPI endpoint.

## Endpoint

POST /api/v1/recommendations/ml

## Authentication

The endpoint depends on the existing get_current_user dependency.

Authentication is not implemented in Phase 14.10.
The current dependency returns HTTP 501 until Phase 18.

Tests override the dependency with a controlled test user.
The endpoint must not accept an arbitrary user_id from the request.

## Request

{
  "resource_ids": [
    "resource-uuid"
  ],
  "prediction_at": "2026-11-08T12:00:00Z"
}

prediction_at is optional and defaults to UTC now.

## Response

The response contains:

- Authenticated user ID
- Model run ID
- Total prediction count
- Resource IDs
- Relevance probabilities
- Relevance decisions
- Generation timestamp

## Architecture

HTTP request
    |
    v
FastAPI route
    |
    v
Authenticated user dependency
    |
    v
ML service dependency
    |
    v
Phase 14.9 RecommendationMLService
    |
    v
Structured API response

## Error handling

- 422: invalid request
- 501: authentication not implemented
- 503: ML service unavailable or inference failure
- 500: response serialization failure

## Boundaries

This phase does not:

- Train models during API requests.
- Accept user IDs supplied by clients.
- Load arbitrary model files from request data.
- Replace rule-based or content-based recommendations.
- Implement Phase 15 hybrid orchestration.
- Implement Phase 18 authentication.

## Verification

The API tests use an injected fake ML service.

A separate integration test must verify the actual
Phase 14.9 service, fitted transformer and model bundle.
# ScholarAI — Phase 14
# Machine Learning Recommendation Model

Version: 1.0
Status: Final Verification Pending
Phase: 14 of 22

---

# 1. Overview

Phase 14 implements a machine-learning-based recommendation
model for ScholarAI.

The purpose is to predict the probability that a learning
resource will be relevant to a particular user.

The ML recommendation model uses:

- User preferences
- Resource metadata
- Resource categories
- Historical user-resource interactions
- Explicit recommendation feedback
- Derived learning-context features

The model is designed to complement the existing:

- Phase 10: Rule-Based Recommendation Engine
- Phase 11: Content-Based Recommendation Engine

Phase 15 will integrate these recommendation strategies
into a unified hybrid recommendation engine.

The ML model does not replace the existing recommendation
systems.

---

# 2. Recommendation Objective

The primary objective is binary relevance prediction.

For a user-resource pair, the model estimates:

P(relevant | user, resource, context)

The prediction is a probability between 0 and 1.

The probability represents the model's estimated likelihood
that the resource is relevant under the training labels
and feature distribution.

It is not a guarantee that the user will consume or benefit
from the resource.

## 2.1 Prediction labels

| Label | Meaning |
|-------|---------|
| 0 | Not relevant |
| 1 | Relevant |

The model learns from explicitly defined interaction
and feedback signals.

Missing interaction data is not automatically interpreted
as negative feedback.

## 2.2 Positive signals

The implemented labeling policy includes:

- Resource clicks
- Resource saves
- Resource completion
- Explicit helpful feedback
- High ratings according to the configured threshold

## 2.3 Negative signals

The implemented labeling policy includes:

- Explicit not-helpful feedback
- Explicit irrelevant feedback
- Low ratings according to the configured threshold

Neutral ratings and passive views are excluded
when the labeling policy specifies exclusion.

The exact thresholds are defined in the labeling
implementation and must not be duplicated as
independent constants in this document.

---

# 3. System Architecture

The Phase 14 implementation is organized into
independent components.

## 3.1 Dataset architecture

Location:

app/services/recommendations/ml/

Responsible for:

- Training-example representation
- Label definitions
- Signal interpretation
- Duplicate user-resource label resolution
- Label provenance
- Dataset schema versioning

## 3.2 Feature engineering

Location:

app/services/recommendations/ml/features/

Responsible for:

- User feature extraction
- Resource feature extraction
- Historical interaction features
- Temporal feature boundaries
- Missing-value handling
- Categorical transformation
- Text feature transformation
- Feature matrix generation

## 3.3 Baseline model

Location:

app/services/recommendations/ml/models/

Responsible for:

- Logistic regression baseline
- Dummy classifier baseline
- Model configuration
- Probability prediction
- Model training summary

The baseline provides a measurable reference
for subsequent recommendation improvements.

## 3.4 Training pipeline

Location:

app/services/recommendations/ml/training/

Responsible for:

- Dataset alignment
- User-separated train/validation splitting
- Feature transformer fitting
- Model training
- Sample weighting
- Training statistics
- Validation dataset preparation

The training pipeline must not fit the feature
transformer on validation data.

## 3.5 Artifact storage

The artifact store is responsible for persisting
trained model artifacts.

Model artifacts and feature transformers must
remain compatible.

Only trusted model artifacts may be loaded.

## 3.6 Evaluation

Location:

app/services/recommendations/ml/evaluation/

Responsible for:

- Classification metrics
- Ranking metrics
- Class imbalance analysis
- Dummy baseline comparison
- Structured evaluation reports

The evaluation process must use held-out
validation data.

## 3.7 Experiment tracking

Location:

app/services/recommendations/ml/experiments/

Responsible for:

- Experiment run identification
- Training configuration recording
- Dataset metadata
- Model metadata
- Evaluation results
- Environment metadata
- Experiment comparison

Experiment metadata must not expose unnecessary
personal identifiers or sensitive information.

## 3.8 Privacy

Location:

app/services/recommendations/ml/privacy/

Responsible for:

- Metadata sanitization
- Identifier leakage detection
- Sensitive feature detection
- Target leakage detection
- Temporal leakage checks
- Dataset privacy validation
- Privacy audit reporting

## 3.9 Inference

Location:

app/services/recommendations/ml/inference/

Responsible for:

- Loading/injecting a compatible model bundle
- Extracting prediction-time features
- Applying the fitted feature transformer
- Predicting relevance probabilities
- Applying the configured threshold
- Producing structured prediction results

Inference must not retrain the model.

---

# 4. Training Data Flow

The training workflow is:

1. Collect available interaction signals.
2. Collect explicit recommendation feedback.
3. Convert signals into labeled examples.
4. Resolve conflicting user-resource labels.
5. Extract features at the appropriate prediction time.
6. Validate feature names and temporal boundaries.
7. Validate dataset privacy requirements.
8. Split users into training and validation groups.
9. Fit the feature transformer on training records.
10. Transform training records.
11. Transform validation records using the fitted transformer.
12. Train the logistic regression baseline.
13. Train the dummy baseline.
14. Evaluate both models on held-out validation data.
15. Store the trained artifact.
16. Record the experiment metadata.

Training and validation users must be separated
according to the configured split policy.

No validation information may be used to fit
the feature transformer.

---

# 5. Evaluation Methodology

Evaluation includes classification and ranking metrics.

## 5.1 Classification metrics

The evaluation implementation includes:

- Accuracy
- Precision
- Recall
- F1 score
- Balanced accuracy
- Confusion matrix
- ROC-AUC
- PR-AUC
- Average precision

Metrics requiring both classes must handle
single-class validation datasets explicitly.

## 5.2 Ranking metrics

The implementation includes:

- Precision@K
- Recall@K
- NDCG@K

Ranking metrics are calculated by user.

The relevance labels must represent ground truth.

Predicted probabilities must not be substituted
for ground-truth relevance labels.

## 5.3 Baseline comparison

The trained logistic regression model is compared
against a dummy classifier.

A trained model should not be considered useful
merely because it completes training.

Its performance must be interpreted against
the dummy baseline and the validation dataset.

No numerical production-quality threshold is
claimed by this document.

---

# 6. Experiment Reproducibility

Each training run must have an identifiable run ID.

The experiment record should preserve:

- Run ID
- Training timestamp
- Model name
- Training configuration
- Training statistics
- Validation statistics
- Class distributions
- Feature names
- Evaluation report
- Environment metadata
- Dataset fingerprint
- Artifact reference
- Experiment tags

The dataset fingerprint currently represents
the validation labels, matrix shape and feature
names.

It must not be described as a cryptographic
fingerprint of the complete underlying dataset.

---

# 7. Privacy and Leakage Prevention

The ML pipeline applies privacy controls
at dataset, feature and experiment boundaries.

## 7.1 Identifier exclusion

Raw user and resource identifiers are used
for internal grouping and auditing.

They must not become model input features.

## 7.2 Sensitive data exclusion

Direct contact information and other
configured sensitive fields must be rejected
or excluded.

## 7.3 Temporal leakage prevention

A feature must not contain information
that would only become available after
the prediction timestamp.

## 7.4 Target leakage prevention

The target label and direct derivatives
of the target must not be model inputs.

## 7.5 Experiment metadata

Experiment records must be sanitized
before persistence.

Sanitization is a defense-in-depth control,
not a guarantee that arbitrary personal
information can always be detected.

## 7.6 Security boundary

Phase 14 privacy checks do not replace
Phase 18 authentication, authorization,
encryption, retention, deletion or
application-wide security controls.

---

# 8. Inference Architecture

The inference service receives:

- User identifier
- Candidate resource identifiers
- Prediction timestamp

It extracts features for the supplied
candidate resources.

The fitted feature transformer converts
the feature records into a model matrix.

The trained model predicts relevance
probabilities.

The service returns structured predictions.

The inference service must:

- Preserve candidate-resource association.
- Preserve prediction ordering where required.
- Use the same feature schema as training.
- Use the fitted transformer from the same
  model bundle.
- Avoid fitting or retraining during inference.
- Reject invalid model bundles.
- Handle empty candidate lists safely.
- Handle missing model configuration explicitly.

---

# 9. API Integration

The ML recommendation API is integrated
through a dedicated FastAPI router.

The documented route is:

POST /api/v1/recommendations/ml

The API accepts candidate resource identifiers
and an optional prediction timestamp.

The authenticated user context is resolved
through the existing authentication dependency.

The route delegates inference to the
injected ML recommendation service.

The API must not train a model during
a recommendation request.

The API must not expose internal user
identifiers in model features.

The final request and response schemas
must match the actual implementation.

Authentication remains dependent on the
existing Phase 18 security work.

---

# 10. Testing Strategy

Phase 14 verification requires:

## Dataset tests

- Label generation
- Label precedence
- Duplicate resolution
- Unknown interaction handling
- Dataset schema validation

## Feature tests

- User feature extraction
- Resource feature extraction
- Historical interaction boundaries
- Missing-value handling
- Text transformation
- Feature matrix consistency

## Model tests

- Valid binary training
- Invalid labels
- Probability prediction
- Class imbalance behavior
- Dummy baseline behavior

## Training tests

- User-separated splitting
- Dataset alignment
- Transformer fit boundaries
- Training reproducibility
- Artifact persistence

## Evaluation tests

- Classification metrics
- Ranking metrics
- Per-user grouping
- Single-class edge cases
- Dummy baseline comparison

## Experiment tests

- Run ID validation
- Duplicate protection
- Metadata serialization
- Persistence and retrieval
- Experiment comparison
- Concurrent-write safety

## Privacy tests

- Identifier leakage
- Sensitive feature rejection
- Target leakage
- Temporal leakage
- Dataset privacy validation
- Metadata sanitization

## Inference tests

- Model availability
- Transformer compatibility
- Feature extraction
- Prediction ordering
- Empty candidates
- Invalid input
- Prediction threshold

## API tests

- Successful request
- Authentication dependency
- Invalid UUID
- Duplicate resource identifiers
- Invalid timestamp
- Missing inference service
- Service errors
- Response schema

---

# 11. Known Limitations

The following limitations must remain visible
until addressed by implementation or later phases.

1. A baseline model is not proof of production-grade
   recommendation quality.

2. Sparse user interaction data can reduce
   model reliability.

3. Historical interactions may not represent
   future user interests.

4. Explicit and implicit feedback can be noisy.

5. The privacy sanitizer cannot guarantee detection
   of every possible sensitive value.

6. Feature-name inspection alone cannot detect
   every form of semantic leakage.

7. Model artifacts must be loaded from trusted
   storage.

8. Authentication and authorization are not
   completed merely by integrating the ML route.

9. The model must be monitored for data drift
   and recommendation quality degradation.

10. A trained model must be evaluated against
    a meaningful validation dataset before
    being considered suitable for deployment.

---

# 12. Phase 14 Acceptance Criteria

Phase 14 can be declared complete only when
the following requirements are verified.

| Requirement | Acceptance condition |
|-------------|----------------------|
| Dataset architecture | Valid training examples and labels |
| Feature engineering | Consistent training and inference features |
| Baseline model | Model trains and predicts probabilities |
| Training pipeline | User-separated validation and no preprocessing leakage |
| Artifact storage | Compatible artifacts can be saved and loaded |
| Evaluation | Classification and ranking metrics verified |
| Experiment tracking | Reproducible metadata can be recorded and retrieved |
| Privacy | Configured privacy and leakage tests pass |
| Inference | Correct predictions for supplied candidates |
| API | Endpoint contracts and error handling verified |
| Regression | Full project test suite passes |
| Documentation | Architecture, limitations and API documented |

A failed acceptance criterion must be recorded
as incomplete.

---

# 13. Phase 15 Boundary

Phase 14 produces an ML recommendation
probability.

It does not implement the hybrid
recommendation orchestrator.

Phase 15 is responsible for combining:

- Phase 10 rule-based recommendations
- Phase 11 content-based recommendations
- Phase 14 ML recommendations

Phase 15 must handle:

- Score normalization
- Strategy weighting
- Deduplication
- Fallback behavior
- Comparative evaluation

These responsibilities must not be
silently moved into Phase 14.

---

# 14. Completion Record

Phase: 14
Name: Machine Learning Recommendation Model

Final status: Pending verification

Implementation commit:
7688d3b — Complete Phase 14.10 ML recommendation API integration

Final verification commit:
To be recorded after Phase 14.11 is completed.

Test results:
To be recorded from the actual test run.

Model evaluation results:
To be recorded from a real training and evaluation run.

Known limitations:
Must be retained and updated based on verification.

Completion decision:
Must be made only after all acceptance criteria
have been verified.