# ScholarAI Opportunity Provider Integration

## Overview

Phase 13.3 implements the external opportunity provider
integration architecture.

## Architecture

app/
    core/
        opportunity_provider_config.py

    integrations/
        opportunities/
            base.py
            exceptions.py
            registry.py
            providers/
                adzuna.py

## Initial Provider

Adzuna.

Official API documentation:

https://developer.adzuna.com/

## Responsibilities

- Provider abstraction
- Provider configuration
- Authentication
- HTTP request management
- Timeout handling
- Retry and exponential backoff
- Rate-limit handling
- Provider registration
- HTTP client lifecycle

## Future Responsibilities

Phase 13.4: Opportunity domain models and schemas.

Phase 13.5: Opportunity discovery service.

Phase 13.6: Normalization and deduplication.

Phase 13.7: Eligibility, deadlines and freshness.

Phase 13.8: Relevance scoring and ranking.

Phase 13.9: API and recommendation integration.

Phase 13.10: Testing and evaluation.