# ScholarAI — Phase 10.7: Ranking and Filtering

## Purpose

Phase 10.7 transforms scored educational resources into
a deterministic, filtered, ranked recommendation list.

It builds on Phase 10.6 without recalculating scores.

## Components

### RecommendationFilteringService

Applies explicit request constraints:

- Active resources only
- Resource type
- Language
- Subject
- Difficulty level
- Completed-resource exclusion

Explicit filters are strict. Missing resource metadata
does not satisfy a requested filter.

### RecommendationRankingService

Ranks eligible resources using:

1. Recommendation score, descending
2. Resource quality, descending
3. Resource UUID, ascending

Duplicate resource IDs are removed after sorting.

The highest-scoring occurrence is retained.

Result limits are applied after deduplication.

Rank positions are consecutive and start at 1.

### RecommendationRankingPipeline

Coordinates filtering and ranking:

1. Receives scored candidates
2. Applies explicit filters
3. Excludes completed resources when requested
4. Sorts eligible candidates
5. Deduplicates resource IDs
6. Applies the requested result limit
7. Assigns rank positions

## Determinism

For identical candidate data, request parameters,
and interaction history, output ordering is stable.

No randomness or score recalculation is introduced.

## Data Integrity

Each resource ID must match its scoring result ID.

The filtering and ranking services do not mutate input
resources, scoring results, or interaction records.

## Security

The services do not query the database.

The future candidate retrieval layer must enforce
appropriate authorization and visibility constraints
before passing candidates to this pipeline.

Authentication remains deferred to Phase 18.

## Future Integration

Phase 10.8 will generate recommendation explanations.

Phase 10.9 will integrate the complete recommendation
pipeline with API endpoints and persistence.

## Non-Goals

- New database tables
- Database migrations
- Authentication implementation
- External educational resource discovery
- Machine learning ranking
- Recommendation explanations
- API endpoint implementation