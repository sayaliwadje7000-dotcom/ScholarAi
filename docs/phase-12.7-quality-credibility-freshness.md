# Phase 12.7 — Resource Quality, Credibility and Freshness

## Objective

Implement deterministic quality evaluation for external educational
resources discovered through the Phase 12 provider integrations.

The quality assessment runs after resource filtering and deduplication.

## Quality dimensions

### 1. Metadata completeness

Measures the availability of useful resource metadata.

Signals:

- Title
- Description
- Authors
- Subject
- Language
- Publication date
- License
- Canonical URL
- Access type

Maximum score: 100.

### 2. Source credibility

Uses configurable provider-level trust scores.

Initial configuration:

| Provider | Score |
|---|---:|
| OpenAlex | 0.90 |
| Crossref | 0.90 |
| Google Books | 0.82 |
| YouTube | 0.65 |
| Unknown provider | 0.50 |

These are initial engineering configuration values.
They are not independently verified claims about individual resources.

### 3. Content freshness

Uses resource-type-specific half-life decay.

Formula:

freshness = 100 * 0.5 ** (age_days / half_life_days)

Resources without publication dates receive a configurable
neutral score and a publication_date_missing flag.

Future publication dates are flagged and receive a neutral score.

## Overall score

Default weights:

- Metadata completeness: 35%
- Source credibility: 35%
- Content freshness: 30%

Formula:

overall_score =
    completeness_score * 0.35
    + credibility_score * 0.35
    + freshness_score * 0.30

All scores use a 0–100 scale.

## Resource enrichment

The assessment is stored in the resource metadata under:

quality_assessment

Fields:

- overall_score
- completeness_score
- credibility_score
- freshness_score
- algorithm_version
- evaluated_at
- flags

The original resource is not mutated.

## Integration order

1. External provider discovery.
2. Provider response validation.
3. Resource filtering.
4. Phase 12.6 normalization and deduplication.
5. Phase 12.7 quality assessment.
6. API response conversion.

## Scope exclusions

This phase does not:

- Rank resources by relevance.
- Generate recommendations.
- Persist external resources.
- Verify individual factual claims.
- Perform machine-learning classification.
- Make additional external API requests.
- Remove low-quality resources automatically.

These responsibilities belong to later roadmap phases.

## Testing

The test suite validates:

- Configuration constraints.
- Metadata completeness.
- Provider credibility.
- Freshness decay.
- Missing and future publication dates.
- Overall weighted scoring.
- Resource enrichment.
- Metadata preservation.
- Non-mutation.
- Batch order preservation.
- Assessment serialization.