# ScholarAI — Opportunity Validity Engine

## Phase

Phase 13.7 — Eligibility, Deadlines and Freshness

## Objective

Implement a validity evaluation subsystem for discovered opportunities.

The subsystem evaluates:

1. Student eligibility.
2. Registration deadlines.
3. Opportunity lifecycle status.
4. Event dates.
5. Data freshness.

It provides structured results for later API and recommendation integration.

---

## Architecture

```text
                 Opportunity
                      |
                      |
          Opportunity Validity Service
                      |
          +-----------+-----------+
          |           |           |
          v           v           v
      Eligibility  Deadline   Freshness
      Evaluator    Evaluator  Evaluator
          |           |           |
          +-----------+-----------+
                      |
                      v
             Validity Result
                      |
                      v
          Future API / Ranking Layer