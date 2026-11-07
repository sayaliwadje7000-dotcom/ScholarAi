New-Item -ItemType Directory -Force -Path "docs" | Out-Null

@'
# ScholarAI — Phase 11 Architecture

## Phase

11 — Content-Based Recommendation Engine

## Subphase

11.1 — Architecture and Existing Infrastructure Audit

## Status

Architecture defined. Implementation has not yet been claimed complete.

---

## 1. Original Phase Objective

The original ScholarAI roadmap defines Phase 11 as:

- Topic/resource features or embeddings.
- Similarity-based ranking.
- Filtering.
- Evaluation.

This document defines the technical architecture for implementing
that objective. The numbered subphase 11.1 is a later implementation
breakdown, not an original roadmap numbering recovered from the source.

---

## 2. Architectural Purpose

The Content-Based Recommendation Engine will recommend educational
resources according to the similarity between:

1. The learning intent expressed by a user.
2. The content and metadata of available educational resources.

The engine must produce an independently measurable content-based
relevance score.

It must not simply reuse the Phase 10 rule-based score.

---

## 3. Existing Infrastructure to Reuse

### Database

Existing StudyResource model.

Relevant fields include:

- title
- description
- resource_type
- subject
- language
- difficulty_level
- estimated_duration_minutes
- quality_score
- resource_metadata
- is_active
- published_at

Important implementation detail:

The Python ORM attribute is resource_metadata.
It maps to the database column named metadata.

### Resource Metadata

Existing ResourceMetadata and ResourceClassification schemas.

Relevant metadata includes:

- topics
- keywords
- learning_objectives
- prerequisites
- content_format
- source_language
- author
- provider
- estimated_reading_minutes
- is_beginner_friendly
- last_verified_at

### User Context

Existing UserPreferences and UserResourceInteraction models.

These may provide learning context and interaction signals.

Personal interaction signals must not be treated as resource content.

### Phase 10 Recommendation Infrastructure

Existing components:

- ResourceClassifier
- LearningContextBuilder
- RecommendationFilteringService
- RecommendationRankingService
- RecommendationExplanationService
- RecommendationApplicationService
- Recommendation and RecommendationFeedback models

Reuse these components only where their contracts and semantics
are compatible with content-based recommendations.

### Phase 8 Embedding Infrastructure

Phase 8 provides embedding and vector-search foundations.

The existing embedding implementation must be inspected before reuse.

Document-chunk embeddings and whole-resource embeddings are distinct
representations and must not be treated as interchangeable.

---

## 4. Proposed Content-Based Architecture

The intended processing pipeline is:

1. Receive recommendation intent.
2. Extract resource content features.
3. Normalize features.
4. Construct a resource representation.
5. Generate or retrieve compatible resource embeddings.
6. Calculate similarity.
7. Produce a content-based score.
8. Filter ineligible candidates.
9. Rank eligible candidates.
10. Generate explanations.
11. Evaluate recommendation quality.

---

## 5. Separation of Recommendation Strategies

Phase 10:
Deterministic rule-based recommendation scoring.

Phase 11:
Content-feature and semantic-similarity recommendation scoring.

Phase 14:
Machine-learning recommendation scoring.

Phase 15:
Hybrid orchestration combining the outputs of Phases 10, 11 and 14.

Each strategy must retain its own score, algorithm version and
evaluation evidence before hybrid integration.

---

## 6. Content Representation

The initial resource representation may include:

- Title
- Description
- Subject
- Resource type
- Topics
- Keywords
- Learning objectives
- Prerequisites
- Content format
- Language
- Difficulty level

Missing metadata must remain missing.

The engine must not invent topics, prerequisites, learning objectives
or other resource properties.

Feature normalization must be deterministic and testable.

---

## 7. Similarity Strategy

The content-based engine will support:

- Structured metadata similarity.
- Semantic embedding similarity.
- A separately calibrated content-based score.

Cosine similarity is the proposed embedding similarity measure.

The final scoring formula and weights must be established and
validated in later implementation and evaluation subphases.

Raw similarity values must not automatically be interpreted as
probabilities or calibrated relevance probabilities.

---

## 8. Data and Persistence Decisions

No database migration is authorized by this architecture document.

Before introducing persistent resource embeddings, inspect:

- Existing Phase 8 vector tables.
- Embedding dimensions.
- Embedding model and version.
- Vector ownership and resource identity.
- Existing indexes.
- Migration history.

If the existing schema cannot safely represent whole-resource
embeddings, design a separate resource-embedding persistence strategy.

Do not store personal user interaction data inside public resource
embeddings.

---

## 9. API and Integration

Phase 11 should integrate with the existing recommendation API
without breaking Phase 10 contracts.

Content-based scoring must remain distinguishable from rule-based
scoring.

Authentication remains subject to the existing Phase 18 security plan.
Do not bypass the current authentication dependency to make an
endpoint appear operational.

---

## 10. Testing and Evaluation

The implementation must eventually cover:

- Feature extraction.
- Feature normalization.
- Missing and malformed metadata.
- Embedding compatibility.
- Similarity calculations.
- Score bounds and determinism.
- Candidate filtering.
- Ranking behavior.
- Duplicate handling.
- Empty candidate sets.
- Sparse resource metadata.
- Evaluation using explicitly labelled relevance data.

Synthetic evaluation data must be identified as synthetic.

---

## 11. Architectural Constraints

1. Do not duplicate Phase 8 embedding providers.
2. Do not duplicate Phase 10 filtering or ranking without justification.
3. Do not mix rule-based and content-based scores.
4. Do not add database tables without a demonstrated requirement.
5. Do not infer missing resource metadata.
6. Do not expose API keys or personal data.
7. Do not bypass authentication.
8. Keep the Phase 11 implementation independently testable.
9. Preserve backward compatibility with Phase 10.
10. Preserve Phase 15 hybrid integration capability.

---

## 12. Proposed Implementation Breakdown

These are implementation subphases proposed for Phase 11.
They are not claimed to be original numbered roadmap tasks.

11.1 Architecture and Existing Infrastructure Audit
11.2 Content Feature Extraction and Normalization
11.3 Resource Content Representation
11.4 Content Embedding Integration
11.5 Similarity Computation Engine
11.6 Content-Based Scoring Engine
11.7 Candidate Filtering and Ranking
11.8 User Query and Learning Context Integration
11.9 Recommendation Service and API Integration
11.10 Evaluation, Testing and Optimization

---

## 13. Completion Criteria for Subphase 11.1

- Original Phase 11 objective preserved.
- Existing Phase 8 and Phase 10 responsibilities identified.
- Resource data sources identified.
- ORM metadata attribute discrepancy documented.
- Content-based architecture defined.
- Scoring separation established.
- Persistence changes deferred until schema audit.
- Future implementation boundaries documented.

---

## 14. Current Status

Architecture specification prepared.

No new database migration, embedding table, API endpoint or
content-based scoring implementation is claimed by Subphase 11.1.

These belong to subsequent subphases.
'@ | Set-Content -Path "docs/phase-11-architecture.md" -Encoding UTF8