# Phase 19.9 — AI Quality Optimization and Comparative Validation

## 1. Objective

Phase 19.9 introduces a reusable optimization framework for comparing
alternative AI configurations against a baseline.

The framework measures objective metrics, enforces quality guardrails,
identifies regressions, and selects the best accepted candidate.

## 2. Architecture

app/evaluation/optimization/
- __init__.py
- schemas.py
- exceptions.py
- strategies.py
- results.py
- validation.py
- runner.py
- reporting.py

tests/evaluation/optimization/
- __init__.py
- test_schemas.py
- test_strategies.py
- test_results.py
- test_validation.py
- test_runner.py
- test_reporting.py

## 3. Optimization workflow

1. Define a baseline candidate.
2. Define candidate configurations.
3. Select an objective metric.
4. Configure improvement requirements.
5. Configure quality guardrails.
6. Evaluate the baseline.
7. Evaluate each candidate.
8. Validate metric observations.
9. Calculate metric means and standard deviations.
10. Compare candidates against the baseline.
11. Reject candidates that violate guardrails.
12. Select the best accepted candidate.
13. Generate a structured optimization report.

## 4. Candidate generation

The candidate generator supports deterministic grid search.

Example:

    generate_candidates({
        "temperature": [0.1, 0.3, 0.5],
        "top_p": [0.8, 0.9]
    })

This produces six candidate configurations.

The maximum candidate limit prevents uncontrolled grid expansion.

## 5. Objective metrics

Examples:

- Answer quality: higher is better.
- Retrieval relevance: higher is better.
- Citation accuracy: higher is better.
- Response latency: lower is better.
- Token consumption: lower is better.
- Inference cost: lower is better.

The objective metric is evaluated separately from guardrail metrics.

## 6. Quality guardrails

Guardrails prevent an optimization from improving one metric while
damaging another important metric.

Example:

    guardrail_limits = {
        "latency": 2.0,
        "cost": 0.05
    }

By default, guardrails are treated as upper limits.

Use guardrails_higher_is_better to configure a metric as a minimum
threshold instead.

A candidate must satisfy every configured guardrail.

## 7. Comparative validation

Each candidate is compared against the baseline using its mean
objective score.

The configured minimum improvement is enforced before acceptance.

This phase does not claim statistical significance. It performs
metric-based comparative validation.

Statistical confidence intervals and hypothesis testing are handled
by the Phase 19.8 experiment framework.

## 8. Evaluation integration

The runner accepts an evaluator callable.

The evaluator receives an OptimizationCandidate and must return:

    {
        "quality": [0.80, 0.82, 0.85],
        "latency": [1.1, 1.2, 1.0]
    }

The evaluator is responsible for executing the actual AI workflow,
such as an LLM, RAG pipeline, recommendation engine, or resource
discovery component.

The optimization framework does not directly modify production
model settings.

## 9. Reporting

Reports include:

- Baseline evaluation.
- Candidate evaluation results.
- Metric means and standard deviations.
- Sample counts.
- Candidate acceptance status.
- Guardrail violations.
- Selected candidate.
- Improvement over baseline.
- Completion and pass status.

Reports can be exported as dictionaries, JSON, and readable text.

## 10. Important limitations

- Candidate generation currently uses grid search.
- Evaluation execution is synchronous.
- The evaluator is injected and must implement the actual AI workload.
- The current comparison uses mean metric values.
- Minimum improvement is an absolute difference in the objective metric.
- This phase does not automatically deploy selected configurations.
- This phase does not establish statistical significance.
- Candidate selection should be followed by controlled experiments
  before production rollout.

## 11. Verification

Run focused tests:

    python -m pytest tests/evaluation/optimization -v

Run the complete test suite:

    python -m pytest -v

## 12. Completion criteria

- [ ] Optimization package created.
- [ ] Schemas and configuration validation implemented.
- [ ] Candidate generation implemented.
- [ ] Evaluation result processing implemented.
- [ ] Baseline comparison implemented.
- [ ] Guardrail validation implemented.
- [ ] Optimization runner implemented.
- [ ] Reporting implemented.
- [ ] Focused tests pass.
- [ ] Full regression suite passes.
- [ ] Git changes reviewed and committed.
