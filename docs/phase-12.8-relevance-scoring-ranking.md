# Phase 12.8 — Relevance Scoring and Resource Ranking

## Objective

Implement deterministic, explainable relevance scoring and ranking
for educational resources discovered by ScholarAI.

The ranking engine prioritizes resources according to their
relationship with the student's search query.

## Responsibilities

- Normalize search queries and resource text.
- Extract meaningful query terms.
- Compare query terms against resource fields.
- Calculate a relevance score from 0 to 100.
- Record matched terms and matched fields.
- Attach relevance assessment metadata.
- Rank resources deterministically.
- Preserve the original resource objects and metadata.

## Scoring Model

| Signal | Weight |
|---|---:|
| Exact title phrase | 30 |
| Title keyword coverage | 25 |
| Subject match | 15 |
| Description relevance | 15 |
| Metadata topics and keywords | 10 |
| Author match | 5 |
| Total | 100 |

These weights are initial configuration values and require
evaluation against a representative search dataset.

## Relevance Metadata

The ranker attaches:

- score
- matched_terms
- matched_fields
- algorithm_version

Metadata key:

relevance_assessment

## Separation of Responsibilities

Phase 12.7 evaluates:

- Completeness
- Provider credibility
- Freshness
- Overall quality

Phase 12.8 evaluates:

- Query relevance
- Matching fields
- Relevance score
- Ranking order

Quality and relevance scores are not interchangeable.

## Ranking Behavior

Resources are ordered by:

1. Relevance score, descending.
2. Title, case-insensitive, ascending.
3. Provider, case-insensitive, ascending.
4. External ID, case-insensitive, ascending.

The deterministic tie-breakers ensure repeatable ordering.

## Integration

The discovery pipeline performs ranking after:

- Provider search
- Request filtering
- Resource normalization
- Deduplication
- Quality assessment

Ranking occurs before API response conversion.

## Database

No database schema change is required.

No resource persistence is introduced by this phase.

## External Services

No additional external API calls are introduced.

## Machine Learning

No machine-learning model is introduced.

No user-interaction history is used.

## Testing

Tests cover:

- Weight validation
- Text normalization
- Stop-word handling
- Exact phrase matching
- Field-level matching
- Metadata matching
- Score boundaries
- Assessment metadata
- Input immutability
- Deterministic ranking
- Ranking order
- Invalid inputs

## Limitations

The initial implementation uses deterministic lexical matching.
It does not understand semantic equivalence, conceptual similarity,
or contextual meaning.

Semantic relevance can be evaluated in a later phase using
the project's embedding and recommendation infrastructure.

## Completion Criteria

- Relevance scoring is independently testable.
- Relevance metadata is attached without mutating source resources.
- Resources are ranked before API conversion.
- Phase 12.7 quality assessment remains independent.
- Existing provider and discovery behavior remains intact.
- Focused and full regression tests pass.