# ScholarAI — Phase 13.10 Evaluation Report

## 1. Objective

Evaluate the reliability, correctness, ranking quality and
performance of the Live Opportunities Discovery subsystem.

## 2. System components evaluated

- Opportunity provider adapters
- Provider registry
- Opportunity discovery service
- Opportunity schemas
- Opportunity normalization
- Opportunity deduplication
- Eligibility evaluator
- Deadline evaluator
- Freshness evaluator
- Quality assessor
- Relevance scorer
- Ranking service
- Opportunity discovery API

## 3. Functional evaluation

The system must demonstrate:

1. Successful multi-provider discovery.
2. Provider failure isolation.
3. Correct provider provenance validation.
4. Consistent opportunity normalization.
5. Duplicate detection.
6. Preservation of source references.
7. Correct eligibility evaluation.
8. Correct registration deadline evaluation.
9. Freshness classification.
10. Quality assessment.
11. Relevance scoring.
12. Deterministic ranking.
13. API request validation.
14. Correct response serialization.

## 4. Recommendation metrics

The evaluation implementation includes:

- Precision@K
- Recall@K
- F1
- DCG@K
- NDCG@K

These metrics require a labeled evaluation dataset.

No recommendation-quality score should be claimed until
the evaluation dataset has been prepared and measured.

## 5. Reliability metrics

The evaluation implementation includes:

- Duplicate rate
- Expired opportunity leakage
- Eligibility violation rate
- Provider success rate

## 6. Performance evaluation

Measure:

- Discovery duration
- Provider response duration
- Normalization duration
- Deduplication duration
- Validity evaluation duration
- Ranking duration
- Complete API duration

## 7. Critical acceptance conditions

- Expired opportunities must not be recommended.
- Cancelled opportunities must not be recommended.
- Definitely ineligible opportunities must not be recommended.
- Unknown eligibility must remain distinguishable from eligible.
- Duplicate opportunities must be consolidated.
- Provider provenance must be preserved.
- One provider failure must not unnecessarily cancel other providers.
- Missing information must never be fabricated.
- Result ordering must be deterministic for equivalent inputs.
- API errors must not expose credentials or sensitive data.

## 8. Evaluation status

Do not mark the evaluation as passed until the complete
test suite has been executed and its output recorded.

## 9. Known issues requiring verification

- Cross-provider identity matching when records have
  different external IDs.
- URL query parameter canonicalization.
- Ranking result accounting and truncation.
- Database metadata check constraint.
- API response compatibility with ranking dataclasses.
- Provider live connectivity and credentials.
- Missing or incomplete opportunity metadata.

## 10. Final conclusion

Phase 13 is complete only when the discovery pipeline,
validity engine, ranking engine and API have passed their
integration and regression tests.