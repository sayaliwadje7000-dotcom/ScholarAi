# Phase 19.6 — Recommendation, Personalization and Discovery Evaluation

## Objective

Establish a repeatable evaluation framework for ScholarAI recommendation,
personalization and educational-resource discovery pipelines.

## Architecture

- schemas.py: benchmark and evaluation contracts.
- dataset.py: dataset loading, validation, persistence and registry.
- metrics.py: ranking, personalization, diversity, novelty and discovery metrics.
- adapters.py: synchronous and asynchronous recommendation pipeline adapter.
- runner.py: benchmark execution and threshold validation.
- reporting.py: structured JSON and human-readable reports.

## Evaluation dimensions

### Ranking quality
- Precision@K
- Recall@K
- Hit Rate@K
- Mean Reciprocal Rank
- Normalized Discounted Cumulative Gain

### Personalization
Preference-tag alignment between user preferences and recommended item metadata.

### Discovery
Relevance among items explicitly marked as discovery candidates.

### Recommendation diversity
Intra-list diversity using Jaccard distance between item tag sets.

### Novelty
Mean inverse normalized popularity.

### Serendipity
Relevant recommendations that were not included in the expected-item set.

## Interpretation and limitations

Metrics measure different properties and must remain separately observable.
They must not be collapsed into a single score without an explicitly justified
weighting and validation methodology.

Tag alignment is a proxy for personalization, not proof of user satisfaction.
Discovery relevance depends on benchmark labels. Popularity-based novelty
depends on correctly normalized popularity values. Serendipity depends on
the quality of the expected-item baseline.

Benchmark datasets must represent realistic users, queries, relevant items
and discovery candidates. Avoid evaluation leakage between training and
evaluation datasets.

## Testing

Focused tests:

`python -m pytest tests/evaluation/recommendations -v`

Full regression suite:

`python -m pytest -v`

## Completion criteria

- [ ] All recommendation evaluation modules created.
- [ ] Benchmark schema and dataset registry validated.
- [ ] Ranking metrics tested.
- [ ] Personalization and discovery metrics tested.
- [ ] Diversity, novelty and serendipity metrics tested.
- [ ] Sync and async adapters tested.
- [ ] Evaluation runner tested.
- [ ] Reporting tested.
- [ ] Full project regression suite passes.
- [ ] Git changes reviewed and committed.
