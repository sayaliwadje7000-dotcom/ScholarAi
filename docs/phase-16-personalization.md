## Phase 16.3 — Learning Activity and Behavioral Signal Processing

### Objective

Convert student learning activities and resource interactions into
normalized behavioral signals for the personalization system.

### Existing Infrastructure Reused

- LearningActivity
- UserResourceInteraction
- User
- SQLAlchemy database session

### New Components

- app/schemas/behavioral_signals.py
- app/services/behavioral_signal_service.py
- app/api/learning_activities.py
- tests/test_behavioral_signal_service.py

### Implemented Capabilities

1. Learning activity event contracts.
2. Resource interaction normalization.
3. Behavioral signal generation.
4. Signal strength normalization.
5. Signal confidence representation.
6. Rating-based positive and negative signals.
7. Activity and interaction aggregation.
8. User-scoped event retrieval.
9. Learning activity recording API.
10. Behavioral signal retrieval API.

### Signal Sources

- Learning activities
- Resource interactions

### Signal Strength

Normalized range:

-1.0 to +1.0

### Signal Confidence

Normalized range:

0.0 to 1.0

### Existing Models

No duplicate activity or interaction models are introduced.

### Database

No new database table is introduced.

No Alembic migration is required.

### API

POST /api/v1/learning-activities/

GET /api/v1/learning-activities/signals

### Important Design Rules

- A resource view is weak evidence.
- A click is weak positive engagement.
- Saving is stronger engagement.
- Completing a resource is strong engagement.
- Ratings provide explicit positive, neutral or negative evidence.
- A recommendation impression is not positive preference evidence.
- Unknown events are ignored.
- Signals are scoped to the authenticated user.

### Evaluation Boundary

Signal weights are initial heuristics.

Empirical calibration is deferred to Phase 19.

### Dependencies

- Phase 16.1 — Personalization Architecture Audit
- Phase 16.2 — Learning Profile and Goal Management

### Next Subphase

Phase 16.4 — Recommendation Feedback Intelligence.
## Phase 16.4 — Recommendation Feedback Intelligence

### Objective

Convert explicit student feedback into reliable personalization
signals and machine-learning training labels.

### Existing infrastructure reused

- RecommendationFeedback
- Recommendation
- RecommendationFeedbackCreate
- RecommendationFeedbackAPIResponse
- Existing recommendation feedback API
- Existing ML RecommendationFeedbackSignal
- Existing label_recommendation_feedback function

### Feedback interpretation

| Feedback | Signal | Label |
|---|---:|---|
| helpful | +1.0 | relevant |
| not_helpful | -1.0 | not_relevant |
| irrelevant | -1.0 | not_relevant |

Missing feedback is not considered negative feedback.

### Components

- RecommendationFeedbackInsight schemas
- FeedbackIntelligenceService
- RecommendationFeedbackSignalAdapter
- Feedback normalization
- User-scoped feedback retrieval
- Explicit feedback label generation
- Positive and negative feedback aggregation

### Data flow

RecommendationFeedback
    -> Recommendation
    -> FeedbackIntelligenceService
    -> Existing ML Labeling Service
    -> RecommendationFeedbackInsight
    -> Behavioral Signal Adapter
    -> Phase 16.5 Personalized Learning Context

### Database changes

No new database table is introduced.

The existing recommendation_feedback table is reused.

### Security and data integrity

- Feedback is loaded through the owning recommendation.
- Feedback from other users is excluded.
- Feedback and recommendation identifiers are checked.
- Feedback is read-only in the intelligence service.
- Missing feedback is never treated as negative.
- Existing one-feedback-per-recommendation constraint remains authoritative.

### Testing

Focused tests cover:
- Feedback normalization
- Positive and negative label generation
- Confidence and signal-strength bounds
- Timestamp normalization
- Ownership checks
- Feedback/recommendation consistency
- Empty feedback collections
- Behavioral signal conversion

Execution is deferred to the consolidated verification stage
after Phase 22.
## Phase 16.5 — Personalized Learning Context Engine

### Objective

Combine student profile information, structured learning goals,
behavioral evidence and explicit recommendation feedback into
one validated personalization context.

### Existing components reused

- LearningContextBuilder
- RecommendationContext
- RecommendationIntent
- LearningProfile data from Phase 16.2
- BehavioralSignal from Phase 16.3
- RecommendationFeedbackInsight from Phase 16.4

### New components

- PersonalizedLearningContext
- LearningGoalContext
- BehavioralEvidenceSummary
- FeedbackEvidenceSummary
- PersonalizationConfidence
- PersonalizedContextEngine

### Capabilities

- Structured and legacy learning-goal normalization
- Behavioral evidence aggregation
- Explicit feedback aggregation
- Recency-aware signal weighting
- Profile completeness assessment
- Confidence calculation
- Sparse-data identification
- Data provenance tracking

### Recency policy

Behavioral signals use a 30-day half-life.

The confidence calculation is a heuristic and requires empirical
evaluation and calibration during Phase 19.

### Sparse-data policy

Insufficient evidence is represented explicitly.

Missing feedback and missing activity are not interpreted as
negative evidence.

### Database changes

No new table or migration is required.

The engine is a pure context-composition service and does not
perform database queries or modify stored preferences.

### Integration

Phase 16.6 consumes the resulting PersonalizedLearningContext
through an explicit adapter to the Phase 15 hybrid recommendation
engine.

### Verification

Focused tests and the complete project test suite are scheduled
for the consolidated verification stage after Phase 22.
## Phase 16.6 — Adaptive Hybrid Recommendation Integration

### Objective

Connect the personalized learning context engine to the Phase 15
hybrid recommendation workflow through a dedicated application
integration layer.

### Components

- `AdaptivePolicyEngine`
- `AdaptiveHybridService`
- `HybridExecutor`
- `AdaptiveRecommendationPolicy`
- `AdaptiveRecommendationResult`

### Integration flow

1. Load the student's learning profile and goals.
2. Build behavioral signals from learning activities and resource
   interactions.
3. Include explicit recommendation feedback.
4. Build the personalized learning context using
   `PersonalizedContextEngine`.
5. Evaluate evidence coverage and confidence.
6. Select an adaptation mode.
7. Delegate candidate discovery and hybrid ranking to the existing
   Phase 15 orchestrator.
8. Return the hybrid result together with its personalization
   context and policy metadata.

### Adaptation modes

- `COLD_START`
- `PROFILE_GUIDED`
- `BEHAVIOR_GUIDED`
- `FEEDBACK_GUIDED`
- `FULL_PERSONALIZATION`

### Safety and ranking boundaries

- Missing evidence is not negative evidence.
- Explicit user preferences remain distinguishable from inferred
  behavioral evidence.
- Sparse evidence is represented explicitly.
- The Phase 15 scoring and ranking primitives are not modified by
  this integration layer.
- A cold-start user continues to receive the existing Phase 15
  hybrid recommendations.
- The integration does not claim that personalization has changed
  candidate ranking until the policy is connected to the verified
  Phase 15 scoring contract.

### Database

No new database table or migration is introduced.

The implementation reuses the existing preference, activity,
interaction, recommendation and feedback records.

### Verification

Focused tests cover policy selection, sparse evidence, user-context
consistency, executor delegation, invalid limits and preservation
of the Phase 15 execution boundary.

Local integration verification remains pending.
## Phase 16.7 — Cold-Start and Sparse-Data Intelligence

### Objective

Provide useful and relevant recommendations when a student has
little or no historical activity.

The system must gradually increase personalization as reliable
preferences, behavioral signals and explicit feedback become
available.

### Components

- `SparseDataAssessor`
- `ColdStartStrategyService`
- `ExplorationAllocator`
- `SparseDataIntelligenceService`

### Evidence sources

1. Explicit learning preferences.
2. Structured learning goals.
3. Resource interaction signals.
4. Learning activity signals.
5. Explicit recommendation feedback.

### Data levels

- `NO_DATA`
- `COLD_START`
- `LIMITED_DATA`
- `MODERATE_DATA`
- `SUFFICIENT_DATA`

### Cold-start strategies

- `GENERAL_DISCOVERY`
- `PROFILE_GUIDED_DISCOVERY`
- `LIMITED_PERSONALIZATION`
- `BEHAVIOR_GUIDED_PERSONALIZATION`
- `FULL_PERSONALIZATION`

### Exploration allocation

The initial exploration targets are:

| Data level | Exploration target |
|---|---:|
| No data | 80% |
| Cold start | 75% |
| Limited data | 65% |
| Moderate data | 40% |
| Sufficient data | 20% |

These are configurable initial policy defaults, not empirically
validated production-optimal values.

### Evidence safeguards

- Missing feedback is not negative feedback.
- Missing interactions are not negative interactions.
- Behavioral personalization requires minimum evidence and
  confidence thresholds.
- Explicit profile preferences remain available when behavioral
  evidence is sparse.
- User-specified hard constraints must be preserved.
- General educational discovery remains available as a fallback.
- The evidence assessment does not modify stored user data.

### Candidate allocation

`ExplorationAllocator` calculates the requested allocation between
exploration and personalized candidates.

It does not create, rank, or score candidates. The candidate
generation layer must supply relevant candidates for each allocation.

### Database

No new database table or migration is required.

The implementation reuses the existing Phase 16.2 profile,
Phase 16.3 behavioral signals, Phase 16.4 feedback and Phase 16.5
personalized context.

### Verification

Unit tests cover:

- Empty user history.
- Profile-only cold start.
- Behavioral evidence thresholds.
- Explicit feedback thresholds.
- Sufficient evidence.
- Missing-evidence neutrality.
- Hard-constraint preservation.
- Candidate allocation.
- Invalid input handling.

The exploration defaults and confidence thresholds require
empirical calibration during Phase 19.
## Phase 16.8 — Student Personalization Controls and API

### Objective

Provide students with API-level control over their learning
preferences and personalization-related settings.

### Implemented components

1. Personalization control request and response schemas.
2. Preference-management service.
3. Student preference retrieval endpoint.
4. Partial preference update endpoint.
5. Preference reset endpoint.
6. Input normalization and validation.
7. User-scoped preference persistence.
8. Schema, service and API tests.

### Persisted preferences

The implementation reuses the existing UserPreferences model.

Supported fields:

- preferred_language
- education_level
- preferred_subjects
- notification_enabled

Learning goals remain managed through the Phase 16.2
learning-profile service.

### API endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | /api/v1/personalization-controls/ | Retrieve controls |
| PATCH | /api/v1/personalization-controls/ | Update controls |
| POST | /api/v1/personalization-controls/reset | Reset controls |

### Reset behavior

Reset restores the following defaults:

- preferred_language = null
- education_level = null
- preferred_subjects = []
- notification_enabled = true

Learning goals, activity history, feedback records and
recommendation history are not deleted.

### Security

Every endpoint depends on get_current_user.

Database queries are scoped to the authenticated user's ID.

The current authentication dependency remains a placeholder.
Production endpoint access depends on Phase 18.

### Database changes

No new table or column is introduced.

The implementation reuses the existing UserPreferences
database model.

### Verification status

Tests are provided for schema validation, service behavior,
user isolation and API behavior.

Execution and integration verification are deferred
until the complete 22-phase implementation is finished.
## Phase 16.9 — Personalization Evaluation and Optimization

### Objective

Establish an offline evaluation framework for measuring the quality
and reliability of personalized recommendations.

The evaluation layer measures ranking quality, recommendation
coverage, feedback signals, confidence calibration, and performance
across sparse-data segments.

### Implementation

Schemas:

- `app/schemas/personalization_evaluation.py`

Service:

- `app/services/recommendations/personalization_evaluation_service.py`

Tests:

- `tests/schemas/test_personalization_evaluation.py`
- `tests/services/recommendations/test_personalization_evaluation_service.py`

### Evaluation metrics

Ranking:

- Precision@K
- Recall@K
- NDCG@K
- Mean Reciprocal Rank

Coverage:

- Percentage of evaluation cases with at least one recommendation.

Feedback:

- Positive feedback count.
- Negative feedback count.
- Neutral feedback count.
- Positive feedback rate among explicit positive and negative feedback.

Calibration:

- Brier score.
- Expected Calibration Error.

Baseline:

- Personalized NDCG compared with baseline NDCG.
- Personalized Precision compared with baseline Precision.

Segmentation:

- No data.
- Cold start.
- Limited data.
- Moderate data.
- Sufficient data.

### Ground-truth requirements

Ranking metrics require explicitly supplied relevant resource IDs.

The evaluation service does not manufacture labels or infer relevance
from missing feedback.

Calibration currently uses whether at least one relevant resource
appears in the recommendation list as an observed utility proxy.
This is not a calibrated probability of student satisfaction.

### Baseline comparison

Baseline comparisons are calculated only when baseline rankings are
provided for evaluation cases.

Both ranking strategies are evaluated against the same relevant
resource set.

### Data and privacy

The evaluation service operates on supplied in-memory evaluation cases.

It does not persist evaluation data, train models, or change student
preferences or recommendation records.

User IDs are used only as evaluation identifiers in the input schema.

### Limitations

- Evaluation quality depends on the quality and representativeness of
  supplied ground-truth labels.
- Synthetic evaluation cases cannot establish production effectiveness.
- Confidence calibration uses a binary utility proxy.
- Feedback may be biased by the students who choose to submit it.
- Baseline comparisons are meaningful only when both rankings use
  equivalent candidate and relevance conditions.
- No production optimization or automatic weight adjustment is performed.

### Verification

Run:

`python -m pytest tests/schemas/test_personalization_evaluation.py -v`

`python -m pytest tests/services/recommendations/test_personalization_evaluation_service.py -v`

The complete project regression suite remains a separate verification
step.
# ScholarAI — Phase 16 Integration Contracts

## 1. Purpose

This document defines the integration boundaries between the
personalization components implemented during Phase 16.

The objective is to prevent duplicate processing, inconsistent
signals, incorrect ownership, and accidental changes to existing
recommendation behavior.

## 2. Architecture

The intended data flow is:

User Preferences
       |
       v
Learning Profile Service
       |
       +-------------------------+
       |                         |
       v                         v
Learning Activities       Resource Interactions
       |                         |
       +------------+------------+
                    |
                    v
          Behavioral Signal Service
                    |
                    v
          Feedback Intelligence
                    |
                    v
       Personalized Context Engine
                    |
                    v
          Sparse Data Assessment
                    |
                    v
          Adaptive Policy Engine
                    |
                    v
          Adaptive Hybrid Service
                    |
                    v
           Phase 15 Hybrid Engine
                    |
                    v
         Personalized Recommendations
                    |
                    v
            Evaluation Service

Preference Controls API
          |
          v
    User Preferences

Learning Profile API
          |
          v
     Learning Goals
     # Phase 16.10 — Documentation, Integration and Completion

## Objective

Consolidate the implementation of Phase 16 and establish a
verifiable integration boundary between personalization and
the existing hybrid recommendation architecture.

## Subphase inventory

| Subphase | Area |
|---|---|
| 16.1 | Personalization Architecture Audit |
| 16.2 | Learning Profile and Goal Management |
| 16.3 | Learning Activity and Behavioral Signal Processing |
| 16.4 | Recommendation Feedback Intelligence |
| 16.5 | Personalized Learning Context Engine |
| 16.6 | Adaptive Hybrid Recommendation Integration |
| 16.7 | Cold-Start and Sparse-Data Intelligence |
| 16.8 | Student Personalization Controls and API |
| 16.9 | Personalization Evaluation and Optimization |
| 16.10 | Documentation, Integration and Completion |

## Architecture components

### Profile and preferences

- Learning profile schemas.
- Learning profile service.
- Learning goal management.
- Personalization preference controls.

### Behavioral evidence

- Learning activity schemas.
- Behavioral signal service.
- Resource interaction signal conversion.
- Feedback intelligence.

### Context and adaptation

- Personalized learning context.
- Confidence assessment.
- Adaptive policy engine.
- Adaptive hybrid service.
- Sparse-data assessment.
- Cold-start strategy.
- Exploration allocation.

### Evaluation

- Precision@K.
- Recall@K.
- NDCG@K.
- Mean Reciprocal Rank.
- Recommendation coverage.
- Feedback statistics.
- Brier score.
- Expected Calibration Error.
- Baseline comparison.
- Sparse-data segment evaluation.

## Integration boundaries

The personalization layer prepares student-specific context and
adaptation policies.

The hybrid recommendation layer remains responsible for candidate
aggregation, ranking, deduplication, filtering and explanations.

The evaluation layer measures output quality without modifying
recommendation behavior.

## Known integration gaps

1. Adaptive policy weights have not yet been proven to affect
   Phase 15 ranking.
2. Exploration ratios have not yet been proven to affect
   Phase 15 candidate allocation.
3. Full authentication remains part of Phase 18.
4. Production evaluation requires representative labelled data.
5. Automated production evaluation workflows are not established.

## Database and migrations

Phase 16 reuses existing user preference, activity, interaction
and recommendation data structures.

No new Phase 16 database migration is introduced by the
implementations documented here.

This does not replace the need to verify the current database
migration state locally.

## Testing

Run the Phase 16 test inventory and the complete project
regression suite before declaring the phase verified.

Historical test results must not be treated as current results.

## Completion status

Implementation supplied: 16.1–16.10.

Runtime verification: pending.

Phase 15 adaptive ranking integration: requires verification
and potentially further implementation.

Authentication: deferred to Phase 18.

Production evaluation: requires representative labelled data.

Phase 16 must not be described as fully production-ready until
these boundaries are resolved.