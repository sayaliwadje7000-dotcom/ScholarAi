# Phase 10.4 — Rule Definition and Configuration

## Objective

Establish a declarative, versioned and validated configuration
system for the ScholarAI recommendation engine.

## Components

### 1. RuleType

Supported rule categories:

- eligibility
- scoring
- boost
- penalty
- exclusion

### 2. RuleOperator

Supported operators:

- equals
- not_equals
- in
- not_in
- contains
- not_contains
- greater_than
- greater_than_or_equal
- less_than
- less_than_or_equal
- exists

### 3. RuleEffect

Supported effects:

- include
- exclude
- add_score
- subtract_score
- multiply_score

### 4. RuleField

Rule fields are explicitly allowlisted.

Supported fields include:

- resource_type
- subject
- difficulty
- language
- quality_score
- category_slugs
- topics
- keywords
- learning_objectives
- prerequisites
- estimated_duration_minutes
- estimated_reading_minutes
- is_beginner_friendly
- preferred_language
- preferred_subjects
- learning_goals
- education_level

Arbitrary expressions and executable code are not permitted.

## RecommendationRule

Each rule contains:

- rule_id
- name
- description
- rule_type
- priority
- enabled
- condition
- effect
- adjustment

Rule identifiers must be unique.

Priority values range from 1 to 10000.
Lower values indicate higher execution priority.

## RecommendationRuleConfiguration

Configuration contains:

- configuration_version
- rules

The configuration provides deterministic enabled-rule ordering
and separation of disabled rules.

## RecommendationRuleRegistry

The registry supports:

- Reading active configuration
- Retrieving enabled rules
- Retrieving disabled rules
- Looking up a rule by identifier
- Registering a new rule
- Removing a rule
- Replacing the complete configuration

Configuration replacement is validated before becoming active.

## Security

Rules are declarative data.

The system does not evaluate Python expressions, execute arbitrary
code, or dynamically import modules based on rule configuration.

Only allowlisted resource and learning-context fields are supported.

## Execution boundary

This phase defines rules but does not execute them.

Rule evaluation and scoring are reserved for Phase 10.6.

## Database

No database changes or migrations are required.

The initial registry is in-memory and versioned.

Persistent rule management and administrative configuration
are outside the scope of this phase.

## Dependencies

- Phase 10.1: Recommendation architecture
- Phase 10.2: Recommendation domain schemas
- Phase 10.3: Resource metadata and classification

## Completion criteria

- Rule schemas implemented.
- Supported operators validated.
- Supported effects validated.
- Rule identifiers validated.
- Duplicate rule identifiers rejected.
- Priority ordering deterministic.
- Enabled and disabled rules separated.
- Rule registry implemented.
- Registry operations tested.
- Complete project test suite passes.