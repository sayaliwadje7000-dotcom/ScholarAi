# ScholarAI Hybrid Recommendation Engine

## 1. Overview

The ScholarAI Hybrid Recommendation Engine combines three
recommendation approaches:

1. Rule-Based Recommendation Engine
2. Content-Based Recommendation Engine
3. Machine Learning Recommendation Model

The purpose is to generate relevant, diverse, explainable and
reliable educational recommendations.

The hybrid engine combines component outputs using normalized
scores, configurable weights, candidate aggregation, eligibility
filtering and deterministic ranking.

## 2. Architecture

The high-level architecture is:

                    USER REQUEST
                         |
                         v
                HYBRID ORCHESTRATOR
                         |
          +--------------+--------------+
          |              |              |
          v              v              v
      RULE-BASED     CONTENT-BASED      ML
      ENGINE          ENGINE          ENGINE
          |              |              |
          +--------------+--------------+
                         |
                         v
                CANDIDATE AGGREGATION
                         |
                         v
                 SCORE NORMALIZATION
                         |
                         v
                 HYBRID WEIGHTING
                         |
                         v
                 ELIGIBILITY FILTER
                         |
                         v
                 HYBRID RANKING
                         |
                         v
                  EXPLANATIONS
                         |
                         v
                API RESPONSE TO USER

## 3. Architectural Components

### 3.1 Hybrid Contracts

File:

app/services/recommendations/hybrid/contracts.py

Responsibilities:

- Define shared recommendation contracts.
- Define component identifiers.
- Define component execution statuses.
- Represent component scores.
- Represent candidate provenance.
- Represent hybrid candidates.
- Represent recommendation batches.

### 3.2 Score Normalization

File:

app/services/recommendations/hybrid/scoring.py

Responsibilities:

- Normalize component scores.
- Handle different score directions.
- Validate score ranges.
- Apply configured component weights.
- Aggregate normalized scores.
- Preserve component contributions.

### 3.3 Candidate Aggregation

File:

app/services/recommendations/hybrid/aggregation.py

Responsibilities:

- Merge candidates from recommendation components.
- Resolve resource identities.
- Deduplicate equivalent resources.
- Merge provenance.
- Preserve component score information.
- Resolve metadata conflicts.

### 3.4 Eligibility Filtering

File:

app/services/recommendations/hybrid/filtering.py

Responsibilities:

- Validate candidate eligibility.
- Check resource validity.
- Check availability.
- Exclude unavailable resources.
- Apply unknown eligibility policies.
- Preserve exclusion reasons.

### 3.5 Hybrid Ranking

File:

app/services/recommendations/hybrid/ranking.py

Responsibilities:

- Rank eligible candidates.
- Apply hybrid scores.
- Resolve ranking ties deterministically.
- Apply recommendation limits.
- Return ranking metadata.

### 3.6 Explanation Generation

File:

app/services/recommendations/hybrid/explanation.py

Responsibilities:

- Explain hybrid scores.
- Explain component contributions.
- Preserve ranking information.
- Generate understandable recommendation summaries.

### 3.7 Orchestration

File:

app/services/recommendations/hybrid/orchestration.py

Responsibilities:

- Execute recommendation providers.
- Isolate component failures.
- Aggregate candidates.
- Calculate scores.
- Resolve eligibility.
- Rank recommendations.
- Report component execution status.
- Support fallback recommendations.

### 3.8 Evaluation

File:

app/services/recommendations/hybrid/evaluation.py

Responsibilities:

- Evaluate recommendation quality.
- Calculate Precision@K.
- Calculate Recall@K.
- Calculate NDCG@K.
- Measure catalog coverage.
- Measure duplicate rate.
- Compare recommendation strategies.
- Run weight experiments.
- Measure ranking consistency.

## 4. Recommendation Components

### Rule-Based Engine

Uses deterministic recommendation rules.

Advantages:

- Predictable behavior.
- Transparent criteria.
- No model inference requirement.
- Useful fallback when ML is unavailable.

### Content-Based Engine

Uses resource characteristics and similarity.

Advantages:

- Topic relevance.
- Resource similarity.
- Useful for content discovery.
- Can operate without extensive interaction history.

### Machine Learning Engine

Uses trained recommendation models.

Advantages:

- Learns recommendation patterns.
- Can incorporate interaction-derived features.
- Supports personalized relevance when suitable data exists.

## 5. Hybrid Scoring

Initial configured weights:

Rule-based: 0.30
Content-based: 0.30
Machine learning: 0.40

These are provisional weights.

They must be evaluated using independent relevance judgments
before being accepted as production-optimal.

## 6. Candidate Identity

Candidate identity is resolved using:

- Stable resource identifiers.
- Canonical URLs where applicable.

Duplicate candidates are merged while preserving provenance.

## 7. Eligibility

Eligibility is independent of recommendation score.

A high score must never override an explicit invalidity,
ineligibility, expiration or unavailability decision.

## 8. Reliability

The orchestrator must support:

- Component failures.
- Disabled providers.
- Partial recommendation availability.
- Empty candidate sets.
- Malformed provider outputs.
- Structured execution reports.

## 9. Evaluation

Recommendation strategies must be compared using the same
evaluation queries and relevance judgments.

Metrics include:

- Precision@K
- Recall@K
- NDCG@K
- Catalog coverage
- Duplicate rate
- Latency
- Ranking consistency

## 10. Architectural Boundaries

The hybrid layer should not duplicate the responsibilities
of the existing recommendation components.

Component-specific scoring and discovery remain in their
respective services.

The hybrid layer provides integration, aggregation,
normalization, ranking, orchestration and evaluation.

## 11. Current Verification Status

Implementation and integration status must be recorded in
the Phase 15 completion report.

Do not mark an architectural component complete merely
because its file exists.