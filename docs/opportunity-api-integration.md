# Phase 13.9 — Opportunity API Integration

## Overview

Phase 13.9 connects opportunity discovery, normalization,
deduplication, validity evaluation and recommendation
ranking through the ScholarAI FastAPI application.

## Base URL

/api/v1/opportunities

## Endpoints

### 1. Discover opportunities

POST /api/v1/opportunities/discover

Discovers opportunities through configured providers,
deduplicates the returned records, evaluates their validity,
and ranks the results.

Example request:

{
    "query": "Python internship",
    "providers": ["adzuna"],
    "opportunity_types": ["internship"],
    "location": "India",
    "is_remote": true,
    "limit_per_provider": 20,
    "max_results": 50,
    "ranking_limit": 20,
    "student_profile": {
        "skills": ["Python", "SQL"],
        "interests": ["AI", "software development"],
        "opportunity_types": ["internship"],
        "academic_year": "3",
        "location": "India"
    }
}

### 2. Get opportunity categories

GET /api/v1/opportunities/categories

Returns the supported opportunity categories.

## Discovery pipeline

1. Validate API request.
2. Resolve application-managed provider registry.
3. Search selected providers.
4. Validate provider results.
5. Normalize opportunity records.
6. Deduplicate matching opportunities.
7. Evaluate eligibility.
8. Evaluate registration deadlines.
9. Evaluate information freshness.
10. Assess information quality.
11. Calculate relevance.
12. Calculate final ranking.
13. Serialize the response.

## Ranking

The Phase 13.8 ranking service calculates:

Final score =
    (Relevance score * 0.70)
    + (Quality score * 0.30)

The ranking service also applies the configured
validity and eligibility constraints.

## Provider failures

Individual provider failures are isolated.

If at least one provider succeeds, the API can return
successful results together with provider failure metadata.

If all selected providers fail, the API returns
HTTP 503.

## Authentication

This endpoint does not yet implement authenticated
student-profile retrieval.

An optional profile can be supplied in the request.

Persistent authenticated personalization belongs
to Phase 18.

## Persistence

This API currently performs discovery and ranking.

It does not persist the returned opportunities.

Database synchronization and stored opportunity
retrieval must be implemented separately.