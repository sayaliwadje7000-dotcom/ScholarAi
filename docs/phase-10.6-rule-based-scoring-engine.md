# Phase 10.6 — Rule-Based Scoring Engine

## Objective

Implement the deterministic rule evaluator and weighted recommendation
scoring engine.

## Components

### RuleEvaluator

Responsibilities:

- Read allowlisted resource and learning-context fields.
- Evaluate declarative conditions.
- Apply eligibility rules.
- Apply exclusion rules.
- Apply scoring adjustments.
- Enforce score boundaries.
- Produce rule evaluation results.

### RecommendationScoringService

Responsibilities:

- Calculate six recommendation factors.
- Normalize individual factor values.
- Apply configured weights.
- Evaluate recommendation rules.
- Produce normalized scoring results.
- Preserve algorithm version information.

## Scoring factors

| Factor | Weight |
|---|---:|
| Topic relevance | 0.35 |
| Learning level | 0.20 |
| Prerequisite compatibility | 0.15 |
| Resource quality | 0.15 |
| Learning objective relevance | 0.10 |
| Freshness | 0.05 |
| Total | 1.00 |

## Scoring equation

S(r,u) = Σ(w_i × f_i(r,u))

The base score is the weighted sum of normalized factor values.

All factor values and the final score must remain in [0,1].

## Factor implementation

### Topic relevance

Uses Jaccard similarity between normalized resource terms
and the student's query and subject terms.

When both query and subject information exist:

- Query similarity: 65%
- Subject similarity: 35%

When no topic intent is available, a neutral value of 0.5 is used.

### Learning level

Compares the explicitly requested difficulty against resource difficulty.

- Exact match: 1.0
- One level difference: 0.5
- Two level difference: 0.0
- Missing information: 0.5

### Prerequisite compatibility

- No declared prerequisites: 1.0
- Declared prerequisites with unknown mastery: 0.5

Interaction history is not treated as proof of mastery.

### Resource quality

Quality score is normalized from its 0–5 scale to [0,1].

Missing quality information receives a neutral value of 0.5.

### Learning objective relevance

Uses Jaccard similarity between resource learning objectives
and student learning goals.

Missing information receives a neutral value of 0.5.

### Freshness

Uses exponential decay with a 365-day half-life:

F(t) = 0.5^(age_days / 365)

Missing publication dates receive a neutral value of 0.5.

## Rule evaluation

Rules are processed in deterministic priority order.

Eligibility behavior:

- Matching exclusion rules reject a resource.
- If enabled inclusion rules exist, at least one must match.
- Disabled rules are ignored.

Scoring behavior:

- ADD_SCORE increases the score.
- SUBTRACT_SCORE decreases the score.
- MULTIPLY_SCORE multiplies the score.
- The score is clamped to [0,1] after each adjustment.

## Output

The scoring service produces RecommendationScoringResult:

- resource_id
- score
- breakdown
- weights
- algorithm_version

Excluded resources return None and are not persisted as scored
recommendations by this service.

## Determinism

When the resource, learning context, rule configuration, weights
and reference time are identical, the scoring output must be identical.

The reference time can be injected for reproducible testing.

## Database

No new database tables or migrations are required.

This phase operates on already classified resources and constructed
learning contexts.

## Security

- No arbitrary expression execution.
- Rule fields are allowlisted.
- User context is supplied by the authenticated application layer.
- The service does not perform database access.

## Dependencies

- Phase 10.1: Recommendation architecture
- Phase 10.2: Recommendation domain schemas
- Phase 10.3: Resource metadata and classification
- Phase 10.4: Rule definition and configuration
- Phase 10.5: User intent and learning context

## Completion criteria

- Rule evaluator implemented.
- All configured operators evaluated.
- Eligibility rules enforced.
- Exclusion rules enforced.
- Scoring adjustments implemented.
- Six scoring factors implemented.
- Scores normalized.
- Algorithm version included.
- Deterministic scoring verified.
- Automated tests pass.
- Complete project suite passes.