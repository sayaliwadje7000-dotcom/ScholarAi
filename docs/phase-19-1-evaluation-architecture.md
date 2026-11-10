# Phase 19.1 — Centralized AI Evaluation Architecture

## Objective

Introduce shared infrastructure for executing existing ScholarAI
evaluators without replacing their domain-specific metric implementations.

## Existing systems retained

The current project already contains independent evaluation
implementations for:

- RAG
- Retrieval
- Educational-resource discovery
- Content-based recommendations
- Hybrid recommendations
- ML recommendations
- Personalization
- Opportunities
- Academic response quality
- Reliability
- Safety

Keep their domain logic and tests intact.

Integrate them through explicit adapters only when their callable
signatures and payload/result types are verified.

## New architecture

- Evaluator: asynchronous contract and input-validation hook.
- EvaluationConfig: run configuration with dataset/model/prompt
  metadata, timeout and retry metadata.
- EvaluationContext: unique execution ID and run metadata.
- EvaluationRegistry: instance-scoped, thread-safe registration
  and lookup.
- EvaluationLifecycle: validated state transitions.
- EvaluationOrchestrator: evaluator resolution, validation,
  timeout enforcement, execution, metric normalization and
  safe error wrapping.
- EvaluationResult: common result envelope retaining domain metrics.
- CallableEvaluatorAdapter: bridge for legacy synchronous and
  asynchronous callables.

## Result contract

Each successful run records:

- Execution ID
- Evaluator ID
- Evaluator type and version
- Execution status
- Domain metrics
- Start and completion timestamps
- Execution duration
- Dataset version
- Model version
- Prompt version
- Non-sensitive tags

Student questions, answers, user IDs, document text, API keys and
provider secrets must not be copied into default metadata.

## Important boundaries

1. This phase does not add HTTP endpoints.
2. Evaluations are not automatically executed during normal
   student requests.
3. This phase does not persist evaluation reports.
4. max_retries is metadata only. Automatic retries are not enabled
   because evaluators may call paid providers or have side effects.
5. Evaluation adapters must receive fixed, labelled evaluation inputs.
6. Existing domain evaluators remain the source of truth for their
   metric definitions.
7. The orchestrator does not mutate production models, student
   profiles, recommendation state or application databases.

## Integration pattern

Register an adapter around an existing callable only after
verifying its invocation contract.

Illustrative example:

```python
adapter = CallableEvaluatorAdapter(
    evaluator_id="resource-discovery-v1",
    evaluator_type=EvaluatorType.DISCOVERY,
    operation=lambda payload: existing_discovery_evaluator.evaluate(
        ranked_resource_ids=payload["ranking"],
        relevance=payload["relevance"],
        k=payload.get("k", 10),
    ).to_dict(),
)

registry.register(adapter)