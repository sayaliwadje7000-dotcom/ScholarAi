# ScholarAI
## Phase 12.2 — External Resource Provider Research and Selection

**Phase:** 12 — Online Educational Resource Discovery  
**Subphase:** 12.2 — External Resource Provider Research and Selection  
**Status:** Research and selection complete  
**Architecture:** Provider Adapter Architecture

---

## 1. Objective

Identify and evaluate external educational resource providers for ScholarAI.

The selected providers must support reliable discovery of educational videos, academic publications, books and other relevant learning materials.

Provider selection considers:

- API availability and stability.
- Educational relevance.
- Metadata quality.
- Authentication requirements.
- Rate limits.
- Cost and usage restrictions.
- Licensing and data reuse policies.
- Reliability and scalability.
- Integration complexity.

## 2. Selected Providers

### 2.1 YouTube Data API v3

Category: Educational videos  
Status: Selected  
Priority: P0

Responsibilities:

- Search educational videos.
- Retrieve video titles and descriptions.
- Retrieve channel information.
- Retrieve publication dates.
- Retrieve duration and relevant metadata.
- Construct canonical video URLs.

Constraints:

- Default search quota is 100 search requests per day.
- Quota must be monitored.
- API data caching and refresh policies must be respected.
- YouTube audiovisual content must not be downloaded or redistributed through the API.
- YouTube attribution and playback requirements must be preserved.

Official documentation:
https://developers.google.com/youtube/data/getting-started

Developer policies:
https://developers.google.com/youtube/terms/developer-policies

### 2.2 OpenAlex API

Category: Academic research  
Status: Selected  
Priority: P0

Responsibilities:

- Search scholarly works.
- Retrieve authors and publication metadata.
- Retrieve research topics.
- Retrieve open-access locations.
- Retrieve publication dates.
- Support academic resource discovery.

Constraints:

- Use an API key for production-scale access.
- Monitor daily usage and rate limits.
- Respect open-access license metadata.
- Distinguish open access from permission to redistribute.

Official documentation:
https://help.openalex.org/api/

### 2.3 Crossref REST API

Category: Scholarly metadata and DOI discovery  
Status: Selected  
Priority: P0

Responsibilities:

- Search academic publications.
- Retrieve DOI identifiers.
- Retrieve author and publisher metadata.
- Retrieve journal information.
- Retrieve publication dates.
- Retrieve abstracts where available.
- Support metadata enrichment and duplicate identification.

Constraints:

- Include a valid application email using the polite pool.
- Respect request and concurrency limits.
- Use DOI identifiers for cross-provider matching.

Official documentation:
https://www.crossref.org/documentation/retrieve-metadata/rest-api/

### 2.4 Google Books API

Category: Books and textbooks  
Status: Selected  
Priority: P1

Responsibilities:

- Search books and textbooks.
- Retrieve titles and authors.
- Retrieve publishers.
- Retrieve ISBN identifiers.
- Retrieve publication dates.
- Retrieve descriptions and preview information.

Constraints:

- Respect API terms and content restrictions.
- Distinguish preview availability from full access.
- Account for geographic restrictions.

Official documentation:
https://developers.google.com/books/docs/v1/using

Terms:
https://developers.google.com/books/terms

## 3. Deferred Providers

### 3.1 Semantic Scholar API

Status: Deferred  
Priority: P2

Potential responsibilities:

- Academic paper search.
- Author discovery.
- Citation metadata.
- Related-paper recommendations.

Reason for deferral:

The introductory authenticated API rate is one request per second. Additional integration should be justified by measurable improvements over OpenAlex and Crossref.

Official documentation:
https://www.semanticscholar.org/product/api

### 3.2 General Web Search

Google Custom Search JSON API is not selected because its documentation states that it is closed to new customers.

Alternative general web discovery infrastructure requires separate evaluation.

## 4. Provider Selection Matrix

| Category | Provider | Decision | Priority |
|---|---|---|---|
| Videos | YouTube Data API | Selected | P0 |
| Academic research | OpenAlex | Selected | P0 |
| DOI metadata | Crossref | Selected | P0 |
| Books | Google Books | Selected | P1 |
| Additional academic search | Semantic Scholar | Deferred | P2 |
| General web search | Google Custom Search | Rejected | — |
| Online courses | Not selected | Further evaluation | P2 |
| Technical documentation | Not selected | Further evaluation | P2 |
| Open educational resources | Not selected | Further evaluation | P2 |

## 5. Integration Architecture

ScholarAI will use independent provider adapters.

Target structure:

app/
    integrations/
        educational_resources/
            base.py
            registry.py
            providers/
                youtube.py
                openalex.py
                crossref.py
                google_books.py

Provider-specific implementations must remain independent.

Every provider must eventually return a normalized external resource representation.

## 6. Normalized Resource Contract

Proposed fields:

- provider
- external_id
- title
- description
- resource_type
- canonical_url
- authors
- subject
- language
- published_at
- retrieved_at
- license
- access_type
- metadata

The normalized representation will be evaluated against the existing StudyResource model during Phase 12.4.

## 7. Configuration Strategy

Proposed environment variables:

YOUTUBE_API_KEY  
OPENALEX_API_KEY  
CROSSREF_MAILTO  
GOOGLE_BOOKS_API_KEY  
RESOURCE_DISCOVERY_ENABLED  
RESOURCE_DISCOVERY_TIMEOUT_SECONDS  
RESOURCE_DISCOVERY_MAX_CONCURRENCY  
RESOURCE_DISCOVERY_MAX_RETRIES

Credentials must remain backend-only.

Configuration will be introduced during Phase 12.3.

## 8. Reliability Requirements

The resource discovery system must:

1. Isolate provider failures.
2. Use request timeouts.
3. Retry transient failures with bounded exponential backoff.
4. Respect provider-specific rate limits.
5. Limit concurrent requests.
6. Validate provider responses.
7. Support partial results.
8. Report provider health.
9. Avoid logging credentials.
10. Avoid exposing provider API keys to the frontend.

## 9. Licensing and Content Access

ScholarAI must distinguish:

- Discoverable resources.
- Publicly accessible resources.
- Open-access publications.
- Openly licensed content.
- Preview-only resources.
- Restricted resources.

Discovery does not grant redistribution rights.

ScholarAI will link to original sources and will not redistribute copyrighted third-party content without appropriate permission.

Provider-specific caching and display policies must be implemented.

## 10. Implementation Dependencies

| Subphase | Dependency |
|---|---|
| 12.3 Provider integration and API abstraction | This provider selection |
| 12.4 External resource data models and schemas | Provider metadata |
| 12.5 Resource discovery and search service | Provider adapters |
| 12.6 Normalization and deduplication | Common resource contract |
| 12.7 Quality and freshness evaluation | Normalized metadata |
| 12.8 Relevance scoring and ranking | Quality and discovery results |
| 12.9 Recommendation engine integration and API | Completed discovery pipeline |
| 12.10 Testing and optimization | Integrated system |

## 11. Completion Criteria

Phase 12.2 is complete when:

- Primary providers have been researched.
- Provider capabilities and limitations are documented.
- Provider selections are recorded.
- Deferred providers are identified.
- Authentication requirements are documented.
- Rate limits and licensing constraints are documented.
- The adapter architecture is defined.
- The normalized resource contract is proposed.
- Implementation dependencies are established.

## 12. Final Decision

Selected primary providers:

1. YouTube Data API v3.
2. OpenAlex API.
3. Crossref REST API.
4. Google Books API.

Deferred:

1. Semantic Scholar.
2. Additional online course providers.
3. Technical documentation providers.
4. Open educational resource providers.

The implementation will begin in Phase 12.3.

No provider integration code or API credentials are introduced by this research phase.