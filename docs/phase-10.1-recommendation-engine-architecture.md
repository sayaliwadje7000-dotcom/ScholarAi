# Phase 10.1 — Rule-Based Recommendation Engine Architecture

## 1. Objective

Establish a modular, deterministic, explainable recommendation
architecture for ScholarAI.

The engine will recommend educational resources based on
user learning preferences, learning objectives, resource
metadata, educational suitability and interaction history.

The architecture must support future content-based,
machine-learning and hybrid recommendation systems.

## 2. Architecture Principles

- Separation of concerns
- Deterministic scoring
- Configurable recommendation rules
- Explainable recommendations
- User-level data isolation
- Transactional persistence
- Reusable existing database models
- Extensibility for future recommendation algorithms

## 3. Service Components

### RuleConfig
Defines scoring weights, thresholds and algorithm version.

### ContextBuilder
Constructs user learning context using preferences
and historical resource interactions.

### CandidateService
Retrieves candidate educational resources from PostgreSQL.

### EligibilityService
Filters resources according to availability,
learning suitability and exclusion rules.

### ScoringService
Calculates normalized weighted recommendation scores.

### RankingService
Sorts candidates and applies deterministic tie-breaking,
deduplication and result limits.

### ExplanationService
Creates human-readable explanations from scoring results.

### RecommendationService
Coordinates the complete recommendation workflow.

### Recommendation API
Provides authenticated endpoints for recommendation
generation and retrieval.

## 4. Recommendation Workflow

1. Receive authenticated recommendation request.
2. Construct user learning context.
3. Retrieve user preferences.
4. Retrieve relevant interaction history.
5. Retrieve candidate resources.
6. Apply eligibility rules.
7. Calculate scoring factors.
8. Calculate normalized weighted scores.
9. Rank and deduplicate candidates.
10. Generate explanations.
11. Persist recommendations.
12. Return structured API response.

## 5. Scoring Configuration

| Factor | Weight |
|---|---:|
| Topic relevance | 0.35 |
| Learning-level suitability | 0.20 |
| Prerequisite compatibility | 0.15 |
| Resource quality | 0.15 |
| Learning objective match | 0.10 |
| Freshness | 0.05 |
| Total | 1.00 |

All individual scoring factors must be normalized
between 0 and 1.

The final score must also remain between 0 and 1.

Missing metadata must be handled explicitly.
It must not automatically produce a perfect score.

## 6. Database Integration

Existing models:

- User
- UserPreferences
- StudyResource
- ResourceCategory
- UserResourceInteraction
- Recommendation
- RecommendationFeedback

No duplicate recommendation tables will be created.

The existing synchronous SQLAlchemy session architecture
will be retained.

## 7. Persistence

Persist:

- User ID
- Resource ID
- Recommendation type
- Normalized score
- Rank position
- Explanation
- Status
- Algorithm version
- Scoring metadata
- Generation timestamp
- Optional expiration timestamp

Recommendation persistence must be transactional.

## 8. Security

All personalized recommendation operations must use
the authenticated user identity.

The engine must never accept an arbitrary user ID
from an untrusted request to determine ownership.

Authentication remains governed by the existing
authentication dependency and Phase 18 roadmap.

## 9. Determinism

Identical user context, candidate resources,
scoring configuration and algorithm version must
produce identical scores and rankings.

Tie-breaking must use stable resource identifiers
after comparing recommendation scores.

## 10. Future Extensibility

The architecture must support:

- Phase 11: Content-Based Recommendation Engine
- Phase 12: Online Educational Resource Discovery
- Phase 13: Live Opportunities Discovery
- Phase 14: Machine Learning Recommendation Model
- Phase 15: Hybrid Recommendation Engine Integration
- Phase 16: Personalized Learning and Adaptive Recommendations

Future algorithms must be independently implementable
and integrate through clearly defined service contracts.

## 11. Completion Criteria

Phase 10.1 is complete when:

- Architecture is documented.
- Service boundaries are defined.
- Data flow is documented.
- Scoring configuration is established.
- Existing database integration is documented.
- Persistence contract is established.
- Authentication requirements are documented.
- Future extensibility is documented.