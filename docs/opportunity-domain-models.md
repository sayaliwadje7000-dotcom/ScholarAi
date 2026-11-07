# ScholarAI — Opportunity Domain Models

## Phase

Phase 13.4 — Opportunity Domain Models and Schemas.

## Objective

Establish a standardized opportunity domain for storing, validating,
and transferring opportunity information across ScholarAI.

The domain is designed to support opportunities discovered through
external providers integrated during Phase 13.3.

## Supported opportunity categories

- Hackathon
- Internship
- Competition
- Workshop
- Conference
- Academic event
- Scholarship
- Other

## Database model

Table: `opportunities`

Primary key: `id` (UUID)

External identity:

- provider
- external_id

The combination of provider and external_id is unique when the
external identifier is present.

## Opportunity information

The model stores:

- Title
- Description
- Organizer
- Opportunity category
- Official URL
- Source URL
- Application URL
- Eligibility requirements
- Required skills
- Location
- Remote availability

## Registration and event dates

Registration dates and event dates are stored separately.

Registration:

- registration_start
- registration_deadline

Event:

- event_start
- event_end

Date ordering is validated by the domain schema and database
constraints.

All timestamps must be timezone-aware at the schema boundary.

## Lifecycle status

Supported states:

- discovered
- validated
- open
- registration_closed
- cancelled
- postponed
- expired
- completed

## Verification status

Supported states:

- official_verified
- secondary_verified
- unverified
- conflicting
- unavailable

Verification is separate from lifecycle status.

An opportunity can be open while its information remains unverified.

## Provider metadata

The PostgreSQL JSONB metadata column stores provider-specific
information that does not belong in the normalized domain fields.

The Python ORM attribute is `opportunity_metadata` because
SQLAlchemy declarative models reserve the class-level `metadata`
attribute.

The Pydantic schema exposes the field as `metadata`.

## Integrity constraints

The database enforces:

- Unique provider/external identifier pairs.
- Non-empty provider names.
- Non-empty titles.
- Valid opportunity categories.
- Valid lifecycle states.
- Valid verification states.
- Registration date ordering.
- Event date ordering.
- JSON array type for required skills.
- JSON object type for metadata.

## Indexing

Indexes support queries by:

- Provider
- Opportunity category
- Lifecycle status
- Verification status
- Registration deadline
- Event start
- Retrieval time
- Category/status/deadline combination

## Architecture

Provider integrations:

`app/integrations/opportunities/`

Domain model:

`app/models/opportunity.py`

Pydantic schemas:

`app/schemas/opportunities.py`

Database migrations:

`alembic/versions/`

Tests:

- `tests/models/test_opportunity_model.py`
- `tests/schemas/test_opportunity_schemas.py`

## Future integration

Phase 13.5 will consume these models and schemas when implementing
the opportunity discovery service.

Phase 13.6 will handle normalization and deduplication.

Phase 13.7 will implement eligibility, deadlines and freshness.

Phase 13.8 will implement quality and relevance ranking.

Phase 13.9 will integrate the opportunity functionality into the
FastAPI API and recommendation infrastructure.