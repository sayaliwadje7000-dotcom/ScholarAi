# Phase 14.2 — Dataset Architecture and Label Definition

## Objective

Establish a consistent and versioned training dataset architecture
for the ScholarAI machine-learning recommendation system.

## Dataset Contract

Each training example contains:

- user_id: Internal grouping identifier.
- resource_id: Internal grouping identifier.
- label: Relevance target.
- label_source: Source of the label.
- source_event: Observed event.
- observed_at: Event timestamp.
- schema_version: Dataset contract version.
- confidence: Label confidence.

## Label Definitions

| Event | Label |
|---|---|
| Click | 1 |
| Save | 1 |
| Complete | 1 |
| Rating 4–5 | 1 |
| Rating 1–2 | 0 |
| Rating 3 | Excluded |
| Helpful feedback | 1 |
| Not helpful feedback | 0 |
| Irrelevant feedback | 0 |
| View | Excluded |
| Missing interaction | Excluded |

## Important Rules

1. Missing interactions are not negative labels.
2. Explicit feedback takes precedence over implicit interactions.
3. The latest event wins within the same signal category.
4. Neutral events are excluded.
5. User and resource identifiers are grouping keys, not model features.
6. All timestamps must be timezone-aware.
7. Dataset schema versions must be validated.

## Implementation

- dataset_schema.py
- labeling.py
- __init__.py

## Tests

- test_dataset_schema.py
- test_labeling.py

## Next Phase

Phase 14.3 — Feature Engineering and Feature Pipeline.