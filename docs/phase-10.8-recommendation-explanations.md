# ScholarAI — Phase 10.8: Recommendation Explanations

## 1. Objective

Implement a deterministic explanation layer that communicates
why an educational resource was recommended.

Explanations are derived from recommendation scoring results,
resource metadata, and the user's learning context.

## 2. Architecture

Ranking Pipeline
       |
       v
RecommendationExplanationService
       |
       +-- Factor Analysis
       |
       +-- Weighted Contribution Analysis
       |
       +-- Highlight Selection
       |
       +-- Reason Generation
       |
       v
RecommendationExplanation

## 3. Supported Scoring Factors

1. Topic Relevance
2. Learning Level
3. Prerequisite Compatibility
4. Resource Quality
5. Learning Objective Relevance
6. Content Freshness

## 4. Weighted Contribution

Each factor contributes:

weighted_contribution = factor_score * factor_weight

This allows the explanation service to identify which
factors contributed most to the recommendation score.

## 5. Explanation Generation

The service produces:

- Resource UUID
- Recommendation rank
- Recommendation score
- Human-readable reason
- Up to three highlights
- Six factor explanations
- Scoring algorithm version
- Explanation version

## 6. Reliability Principles

- Explanations are deterministic.
- Original ranking order is preserved.
- Missing metadata is not fabricated.
- Unknown prerequisite mastery is not assumed.
- Missing quality ratings are explicitly identified.
- Missing publication dates are explicitly identified.
- Scoring results are not recalculated.
- No LLM dependency is introduced.

## 7. Security

The explanation service does not access the database
or independently retrieve user information.

It operates only on the context and ranked resources
provided by the recommendation pipeline.

Authentication remains deferred to Phase 18.

## 8. Future Integration

Phase 10.9 will integrate recommendation generation,
filtering, ranking, explanations, and persistence
through the recommendation API.

## 9. Non-Goals

- LLM-generated explanations
- Database migrations
- Recommendation API endpoints
- Authentication implementation
- External resource discovery
- Machine learning explanations

## 10. Version

Explanation algorithm: v1
Scoring algorithm: rule-based-v1