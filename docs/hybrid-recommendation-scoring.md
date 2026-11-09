# Hybrid Recommendation Scoring

## 1. Objective

The hybrid scoring engine combines outputs from three
recommendation components into a common ranking score.

The components are:

- Rule-Based
- Content-Based
- Machine Learning

## 2. Score Normalization

Different recommendation components may produce scores
with different ranges and meanings.

Normalization converts compatible component scores into
a common scale.

The initial normalized scale is:

0.0 to 1.0

The score direction must also be considered.

HIGHER_IS_BETTER:
Higher values indicate better recommendations.

LOWER_IS_BETTER:
Lower values indicate better recommendations and must
be inverted during normalization.

## 3. Initial Hybrid Weights

| Component | Weight |
|---|---:|
| Rule-Based | 0.30 |
| Content-Based | 0.30 |
| Machine Learning | 0.40 |
| Total | 1.00 |

These weights are provisional and subject to evaluation.

## 4. Weighted Aggregation

For available normalized component scores:

Hybrid Score =
    (Rule Score × Rule Weight)
  + (Content Score × Content Weight)
  + (ML Score × ML Weight)

When a component is unavailable, the aggregation layer
must apply its configured missing-component policy.

If available weights are renormalized, the effective
weight of each available component is:

Effective Weight =
    Component Weight / Sum of Available Weights

## 5. Missing Scores

A missing component score must not be silently interpreted
as a genuine score of zero.

The system must distinguish:

- Available
- Unavailable
- Failed
- Not Applicable

## 6. Invalid Scores

Invalid scores include:

- NaN
- Positive infinity
- Negative infinity
- Values outside configured ranges

The normalization layer must apply an explicit policy.

## 7. Component Contributions

The system should preserve:

- Raw score.
- Normalized score.
- Configured weight.
- Effective weight.
- Weighted contribution.

These values support explanations and debugging.

## 8. Weight Optimization

Alternative configurations must be evaluated against
validation data.

The final test set must not be repeatedly used for
weight tuning.

A new weight configuration should only be selected
when evaluation evidence supports the change.

## 9. Current Configuration

Default weights:

RULE_BASED = 0.30
CONTENT_BASED = 0.30
MACHINE_LEARNING = 0.40

Production selection status: Pending evaluation.

## 10. Verification

The following must be tested:

- Score normalization.
- Score direction.
- Out-of-range handling.
- Missing components.
- Weight validation.
- Weight renormalization.
- Aggregation determinism.
- Contribution consistency.