# Phase 19.8 — Statistical Analysis and Experiment Management

## 1. Objective

Phase 19.8 introduces a reproducible statistical experimentation framework
for evaluating ScholarAI AI components.

It supports controlled comparisons between baseline and candidate variants,
paired observations, descriptive statistics, bootstrap confidence intervals,
effect sizes, statistical significance, experiment lifecycle management,
and structured reports.

## 2. Architecture

app/evaluation/experiments/
- schemas.py
- exceptions.py
- statistics.py
- validation.py
- registry.py
- comparison.py
- runner.py
- reporting.py

## 3. Experiment configuration

An experiment defines:

- Unique experiment ID
- Baseline variant
- Candidate variant
- Evaluation metric
- Whether higher or lower values are desirable
- Significance level (alpha)
- Minimum observations per variant
- Bootstrap iteration count
- Reproducible random seed
- Minimum practical effect threshold

## 4. Paired experiment design

The framework uses paired comparisons.

Each baseline observation must have a matching candidate observation
with the same sample ID.

For each paired sample:

difference = candidate_value - baseline_value

This design controls for variation between samples and compares the
two variants on equivalent evaluation cases.

The framework rejects:
- Duplicate observations for the same variant and sample
- Unknown variants
- Different experiment IDs
- Different metric names
- Unmatched sample IDs
- Insufficient observations

## 5. Descriptive statistics

The statistics module provides:

- Mean
- Median
- Sample variance
- Population variance
- Sample standard deviation
- Standard error
- Percentiles
- Confidence intervals

## 6. Bootstrap confidence intervals

The comparison module uses bootstrap resampling over paired differences.

For every bootstrap iteration:
1. Randomly sample paired differences with replacement.
2. Calculate the resampled mean difference.
3. Store the resulting mean.
4. Calculate percentile bounds for the configured confidence level.

The random seed makes the bootstrap calculation reproducible.

## 7. Statistical significance

A two-sided normal approximation is used to estimate a p-value from
the paired mean difference and its standard error.

The result is compared with alpha.

A result is statistically significant when:

p_value < alpha

Important:
The p-value calculation uses a normal approximation, not an exact
paired Student-t test or permutation test. Small samples, skewed
distributions, and non-normal differences require additional analysis.

## 8. Practical significance

Statistical significance does not automatically imply practical value.

The experiment also checks whether the absolute mean difference meets
the configured minimum practical effect threshold.

A candidate passes only when:

- Statistical significance is established.
- The candidate moves in the desired metric direction.
- The minimum practical effect threshold is met.

## 9. Effect size

The framework calculates paired Cohen's dz:

mean(paired differences) / standard deviation(paired differences)

A zero-variance non-zero difference produces an infinite effect size.
A zero-variance zero difference produces zero.

Effect sizes must be interpreted in the context of the metric and
the underlying evaluation dataset.

## 10. Experiment lifecycle

Experiment states:

created
completed

The registry supports:
- Create experiment
- Retrieve experiment
- List experiments
- Add observations
- Complete experiment
- Delete experiment

The current registry is in-memory. It is suitable for controlled
evaluation runs and unit tests, but is not durable across process restarts.

Persistent storage and concurrent distributed experiment coordination
are separate production-hardening tasks.

## 11. Reporting

Reports include:
- Baseline and candidate statistics
- Paired sample count
- Mean difference
- Confidence interval
- P-value
- Effect size
- Statistical significance
- Practical significance
- Winner
- Pass/fail decision
- Violations

Reports can be rendered as readable text or exported as JSON.

## 12. ScholarAI integration targets

The experiment framework can compare:

- Different LLM models
- Prompt versions
- RAG retrieval configurations
- Chunking strategies
- Embedding models
- Reranking configurations
- Recommendation algorithms
- Search ranking configurations
- Personalization strategies

Each experiment must use the same benchmark cases across variants
when paired evaluation is intended.

## 13. Statistical limitations

This implementation is an evaluation foundation, not a complete
scientific experimentation platform.

Before using results for high-impact decisions, consider:

- Paired Student-t tests
- Permutation tests
- Multiple-comparison correction
- Power analysis and sample-size planning
- Sequential testing safeguards
- Stratified evaluation
- Bootstrap bias and interval diagnostics
- Distribution and outlier analysis
- Confidence intervals appropriate to the data distribution

The normal-approximation p-value and bootstrap interval should not
be interpreted as interchangeable statistical tests.

## 14. Test coverage

Tests cover:
- Pydantic schemas
- Invalid experiment configurations
- Descriptive statistics
- Confidence intervals
- Bootstrap reproducibility
- Statistical significance
- Effect size
- Observation validation
- Experiment registry
- Experiment lifecycle
- Variant comparison
- Report serialization

## 15. Completion checklist

- [ ] Experiment schemas created
- [ ] Statistical functions implemented
- [ ] Observation validation implemented
- [ ] Experiment registry implemented
- [ ] Paired comparison implemented
- [ ] Bootstrap confidence intervals implemented
- [ ] Experiment runner implemented
- [ ] Reporting implemented
- [ ] Unit tests passed
- [ ] Full project test suite passed
- [ ] Changes committed to Git
