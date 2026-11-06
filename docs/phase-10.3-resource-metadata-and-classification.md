# Phase 10.3 — Resource Metadata and Classification

## Objective

Establish a standardized metadata contract and deterministic
classification mechanism for educational resources.

The classification output will be consumed by the rule-based
recommendation engine.

## Existing database integration

This phase reuses the existing:

- StudyResource
- ResourceCategory
- study_resource_categories
- StudyResource.metadata JSONB database column

No new database table or migration is required.

## Standardized metadata contract

| Field | Type | Purpose |
|---|---|---|
| topics | list[str] | Explicit resource topics |
| keywords | list[str] | Search and matching terms |
| learning_objectives | list[str] | Intended learning outcomes |
| prerequisites | list[str] | Explicit prerequisite knowledge |
| content_format | str | Format of the educational content |
| source_language | str | Language declared by the source |
| author | str | Resource author |
| provider | str | Content provider |
| estimated_reading_minutes | int | Estimated reading time |
| is_beginner_friendly | bool | Explicit beginner suitability |
| last_verified_at | datetime | Last metadata verification |

Unknown metadata fields are preserved through the schema's
extra='allow' configuration.

## Classification output

ResourceClassification provides:

- Resource identity and title
- Resource type
- Subject
- Difficulty
- Language
- Category slugs
- Topics and keywords
- Learning objectives
- Prerequisites
- Content format
- Estimated duration
- Quality score
- Publication date
- Last verification date

## Classification rules

1. Use explicit StudyResource database fields.
2. Read standardized values from JSONB metadata.
3. Normalize text and remove duplicate list values.
4. Normalize category slugs.
5. Preserve missing values as null or empty lists.
6. Never invent missing subjects, prerequisites, topics,
   difficulty levels, or learning objectives.
7. Reject malformed standardized metadata instead of silently
   accepting invalid values.
8. Preserve the original resource record without modifying it.

## Security and data integrity

The classifier does not accept a user ID or access the database.
It operates on resource objects supplied by the calling service.

Database ownership filtering and access control remain the
responsibility of the recommendation service and API layer.

## Dependencies

- Phase 10.1: Recommendation architecture
- Phase 10.2: Recommendation domain schemas

## Downstream integration

Phase 10.4 will define recommendation rules and their configuration.

Phase 10.5 will construct user learning context.

Phase 10.6 will use normalized resource information for scoring.

## Database migrations

None.

## Completion criteria

- Standardized metadata schema implemented.
- Metadata normalization implemented.
- Resource classifier implemented.
- Classification output validated.
- Missing metadata handled safely.
- Invalid metadata rejected.
- Automated tests passing.
- Existing test suite remains green.