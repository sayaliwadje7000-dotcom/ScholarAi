# Phase 17.3 – Intelligent Query Rewriting

## Objective

Implement a deterministic, classification-aware query rewriting
engine for ScholarAI.

The engine prepares student queries for downstream academic
retrieval and AI workflows.

## Architecture

The implementation extends the Phase 17.2 query classifier.

Components:

- QueryRewriteRequest
- QueryRewriteResult
- RewriteStrategy
- QueryRewritingService
- query_rewriting_service

## Processing Pipeline

1. Receive the original student query.
2. Normalize whitespace.
3. Reuse an existing classification or invoke Phase 17.2.
4. Detect context-dependent follow-up queries.
5. Resolve follow-ups using explicitly supplied conversation
   context.
6. Generate a standalone query.
7. Enrich the retrieval query according to academic task type.
8. Generate a bounded list of deduplicated search queries.
9. Return structured rewriting metadata.

## Rewrite Strategies

| Strategy | Purpose |
|---|---|
| unchanged | Original query remains suitable |
| normalized | Whitespace normalization |
| context_resolved | Follow-up resolved using conversation context |
| task_enriched | Retrieval terms added based on academic task |

## Safety and Reliability

- Original queries are preserved.
- Conversation context is optional.
- Context is only used for recognized follow-up queries.
- Context is treated as data, not instructions.
- Search query count is bounded.
- Search queries are deduplicated.
- No additional LLM API call is made.
- No database migration is required.
- No external dependency is introduced.

## Integration Boundaries

The service is independently callable.

It does not yet modify the chat endpoint or execute retrieval.

Conversation history must be explicitly supplied by the future
conversation context management component.

Downstream RAG and resource discovery workflows can consume
standalone_query, retrieval_query, and search_queries.

## Limitations

The rewriting engine is deterministic and rule-based.

It does not perform semantic paraphrasing, LLM-based query
expansion, or learned query optimization.

Those capabilities require separate evaluation and integration.

## Tests

- Query schema validation
- Whitespace normalization
- Academic task enrichment
- Follow-up resolution
- Context isolation
- Document query preservation
- Search query deduplication
- Input boundary validation
- Classification reuse