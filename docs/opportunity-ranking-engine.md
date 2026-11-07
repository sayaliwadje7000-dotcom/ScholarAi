# ScholarAI — Opportunity Ranking Engine

## Phase

Phase 13.8 — Quality Assessment, Relevance Scoring and Ranking

## Objective

Implement a deterministic, explainable opportunity ranking engine.

The system evaluates:

1. Opportunity information quality.
2. Student-opportunity relevance.
3. Opportunity validity.
4. Final ranking position.

## Architecture

Opportunity Discovery
        |
Normalization and Deduplication
        |
Eligibility / Deadline / Freshness
        |
Quality Assessment
        |
Relevance Scoring
        |
Validity Filtering
        |
Composite Ranking
        |
Ranked Opportunity Results

## Quality assessment

The quality assessor evaluates:

| Dimension | Weight |
|---|---:|
| Description | 20% |
| Official URL | 20% |
| Organizer | 15% |
| Registration deadline | 15% |
| Eligibility | 10% |
| Required skills | 10% |
| Provenance | 10% |

This measures information completeness.

It does not establish authenticity or guarantee that an organizer is legitimate.

## Relevance scoring

| Signal | Weight |
|---|---:|
| Skills | 35% |
| Opportunity category | 20% |
| Interests | 20% |
| Location | 10% |
| Academic level | 10% |
| Search query | 5% |

Missing personalization signals are excluded from the denominator.

## Final score

Final score:

    (Relevance score * 0.70)
    +
    (Quality score * 0.30)

All scores are between 0 and 100.

Weights are configurable.

## Validity constraints

The ranking service excludes:

- Inactive opportunities.
- Expired opportunities.
- Cancelled opportunities.
- Closed opportunities.
- Opportunities for which the student definitely fails eligibility.

Unknown eligibility is retained by default.

Stale opportunities may optionally be excluded through configuration.

## Explainability

Each ranked result includes:

- Quality score.
- Relevance score.
- Final score.
- Rank.
- Validity evaluation.
- Explanations.

## Persistence

This phase does not write to PostgreSQL.

It does not modify the Opportunity database model or migrations.

## Future work

Phase 13.9:

- FastAPI integration.
- Opportunity discovery and ranking endpoints.
- Request and response contracts.
- Recommendation integration.

Phase 13.10:

- End-to-end tests.
- Ranking evaluation.
- Quality evaluation.
- Performance optimization.