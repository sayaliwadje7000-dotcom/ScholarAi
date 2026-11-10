# Phase 19.3 — ScholarAI Scoring Engine

## Objective

Build a centralized application scoring system that calculates
meaningful scores for educational resources, search results,
RAG retrieval, opportunities, generated answers and personalized
recommendations.

## Architecture

The scoring subsystem contains:

- BaseScorer
- ScoringConfiguration
- ScoreComponent
- ScoreResult
- ScorerRegistry
- ScoringEngine
- Domain-specific scorers

## Scoring Formula

For normalized component values x and weights w:

Final Score = Sum(x_i * w_i)

Weights are normalized so that their sum equals 1.

Every component score must be between 0 and 1.

## Domain Scorers

1. ResourceScorer
2. SearchScorer
3. RAGScorer
4. OpportunityScorer
5. AnswerScorer
6. PersonalizationScorer

## Important Design Rule

Scoring formulas are domain-specific.

The system must not combine unrelated metrics such as latency,
accuracy, recommendation diversity and token cost into a
single universal quality score.

## Evaluation Relationship

Application scoring produces scores for individual items.

The evaluation metrics library measures the performance of
the scoring and ranking systems across benchmark datasets.

## Limitations

Initial weights are configurable engineering defaults.
They are not empirically optimized or validated yet.

Their calibration and comparative validation belong to
subsequent Phase 19 work.