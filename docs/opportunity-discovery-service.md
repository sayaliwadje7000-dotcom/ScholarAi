# ScholarAI — Opportunity Discovery Service

## Phase

Phase 13.5 — Opportunity Discovery Service

## Objective

Provide a centralized asynchronous service that discovers
opportunities from registered external providers.

The service coordinates provider execution, validates returned
records, applies explicit request filters and aggregates results.

## Architecture

OpportunityDiscoveryRequest
          |
          v
OpportunityDiscoveryService
          |
          v
Provider Selection
          |
          v
Concurrency Controller
          |
          +--------------------+
          |                    |
          v                    v
     Adzuna Provider     Other Providers
          |                    |
          +--------------------+
                   |
                   v
          Provider Validation
                   |
                   v
             Filtering
                   |
                   v
             Aggregation
                   |
                   v
     OpportunityDiscoveryResponse

## Responsibilities

- Provider selection
- Concurrent searches
- Concurrency limiting
- Provider failure isolation
- Provider response validation
- Opportunity category filtering
- Location filtering
- Remote filtering
- Result aggregation
- Overall result limiting

## Provider Contract

A registered provider must expose:

    async def search(
        query: str,
        limit: int,
    ) -> list

Returned records must be compatible with OpportunityCreate.

The provider field must match the registered provider name.

## Failure Isolation

Individual provider exceptions are recorded as provider failures.

A provider failure does not cancel successful provider searches.

If every selected provider fails, the discovery service raises
OpportunityDiscoveryUnavailableError.

A provider returning an empty list is considered successful.

## Concurrency

The service uses asyncio.Semaphore to control the maximum number
of simultaneous provider searches.

The default concurrency limit is four.

## Scope Boundaries

The service does not:

- Persist opportunities.
- Deduplicate records.
- Perform deadline evaluation.
- Determine eligibility.
- Rank opportunities.
- Expose HTTP endpoints.

These responsibilities belong to later Phase 13 subphases.

## Testing

Run:

    python -m pytest tests/services/opportunities -v

The tests use fake providers and do not require external API
credentials.

## Future Integration

Phase 13.6:
Normalization and deduplication.

Phase 13.7:
Eligibility, deadline and freshness evaluation.

Phase 13.8:
Relevance scoring and ranking.

Phase 13.9:
API and recommendation integration.

Phase 13.10:
Testing, evaluation and optimization.