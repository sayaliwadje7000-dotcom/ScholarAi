# Phase 13.6 — Opportunity Normalization and Deduplication

## 1. Objective

Normalize opportunity records received from different external
providers and identify duplicate opportunities.

The system must preserve provider provenance and avoid losing
important opportunity information during merging.

## 2. Components

### OpportunityTextNormalizer

Normalizes text using:

- Unicode NFKC.
- Case folding.
- Whitespace normalization.
- Punctuation normalization.

### OpportunityURLNormalizer

Canonicalizes URLs by removing:

- Tracking parameters.
- Fragments.
- Default ports.
- www prefix.

Meaningful query parameters are preserved.

### OpportunityNormalizer

Converts provider records into a standardized dictionary.

It normalizes:

- Provider names.
- Titles.
- Opportunity types.
- URLs.
- Eligibility.
- Required skills.
- Metadata.

### OpportunityIdentityResolver

Generates deterministic identity fingerprints.

Identity priority:

1. Canonical official URL.
2. Provider and external identifier.
3. Title, organizer, opportunity type and event year.

A title-only match is not sufficient.

### OpportunityDeduplicationService

Identifies records with matching identities and merges them.

It preserves:

- Provider references.
- External identifiers.
- Source URLs.
- Application URLs.
- Required skills.
- Eligibility information.
- Metadata.

## 3. Source provenance

Additional source references are stored under:

metadata.sources

Each reference records:

- Provider.
- External ID.
- Official URL.
- Source URL.
- Application URL.

## 4. Conflict handling

Conflicting eligibility information is preserved under:

metadata.eligibility_conflicts

Other conflicting metadata is preserved under:

metadata.metadata_conflicts

Conflicting optional fields are preserved under:

metadata.field_conflicts

The first record remains the canonical in-memory record.
Conflicting values are not silently discarded.

## 5. Scope exclusions

This phase does not implement:

- Deadline validation.
- Expiry evaluation.
- Eligibility evaluation.
- Quality assessment.
- Relevance ranking.
- Database persistence.
- API integration.

These responsibilities belong to subsequent Phase 13 subphases.

## 6. Limitations

The current identity resolver uses deterministic matching.

It does not automatically merge opportunities solely because
their titles look similar.

Fuzzy matching requires separate evaluation before production use.