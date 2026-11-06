# Phase 10.5 — User Intent and Learning Context

## Objective

Construct a normalized representation of a student's learning
preferences, recent resource interactions and immediate recommendation
intent.

## Components

### RecommendationIntent

Represents the current recommendation request.

Fields:

- query
- subject
- resource_types
- difficulty_level
- language
- recommendation_type
- exclude_completed

### RecommendationContext

Combines:

- LearningContext
- RecommendationIntent
- Context version

### LearningContextBuilder

Constructs the context using:

- User identity
- UserPreferences
- Current recommendation request
- Recent resource interactions

## Preference precedence

An explicit request language takes precedence over the stored
preferred language.

An explicit request subject is added to stored preferred subjects.

Stored learning goals and education level are preserved.

## Interaction history

The builder:

1. Reads supplied interaction records.
2. Validates interaction data.
3. Skips malformed records.
4. Sorts valid records by occurrence time.
5. Retains only the most recent configured number.
6. Converts records into InteractionSummary objects.

Default maximum interaction history: 20 records.

The interaction limit is configurable when constructing the builder.

## Data integrity

The builder does not modify:

- User records
- User preferences
- Interaction history

Missing preferences remain null or empty lists.

The builder does not infer learning goals, preferred subjects,
education level or other missing personal information.

## Database integration

No new database tables or migrations are required.

The builder operates on supplied objects and does not issue
database queries.

Database retrieval and user ownership enforcement remain the
responsibility of the calling API or application service.

## Security

The builder requires a user object with an ID.

The authenticated-user dependency remains responsible for
establishing the identity of the requesting user.

The builder does not accept a client-supplied user ID as
a substitute for authentication.

## Dependencies

- Phase 10.1: Recommendation architecture
- Phase 10.2: Recommendation domain schemas
- Phase 10.3: Resource metadata and classification
- Phase 10.4: Rule definition and configuration

## Downstream integration

Phase 10.6 will use the resulting learning context and
recommendation intent as inputs to rule evaluation and scoring.

## Database migrations

None.

## Completion criteria

- Recommendation intent schema implemented.
- Combined recommendation context implemented.
- User preferences integrated.
- Request intent integrated.
- Interaction history normalized.
- Interaction history bounded.
- Missing preferences handled safely.
- Invalid interactions handled safely.
- Existing user data remains unchanged.
- Automated tests pass.
- Complete project test suite passes.