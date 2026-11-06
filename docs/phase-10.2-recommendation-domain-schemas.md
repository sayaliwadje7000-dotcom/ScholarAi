# Phase 10.2 — Recommendation Domain Schemas

## Objective

Establish validated Pydantic contracts for the ScholarAI
rule-based recommendation engine.

The schemas define communication between recommendation
services, persistence operations and future API endpoints.

## Technology

- Python
- Pydantic v2
- UUID
- Decimal
- Enum
- datetime

## Implemented Contracts

### 1. RecommendationRequest

Defines recommendation generation inputs.

Includes:

- Query
- Subject
- Resource types
- Difficulty
- Language
- Recommendation type
- Result limit
- Completed-resource exclusion

User identity is deliberately excluded.

### 2. LearningContext

Represents the authenticated user's learning context.

Includes:

- User ID
- Preferred language
- Education level
- Preferred subjects
- Learning goals
- Recent interactions

### 3. InteractionSummary

Represents individual resource interactions.

Supports:

- View
- Click
- Save
- Rate
- Complete

Rating validation is enforced.

### 4. RecommendationCandidate

Represents a normalized educational resource.

Includes:

- Resource ID
- Title
- Description
- Resource type
- URL
- Provider
- Subject
- Language
- Difficulty
- Duration
- Quality score
- Categories
- Publication timestamp
- Active status

### 5. RecommendationWeights

Defines configurable scoring weights.

| Factor | Weight |
|---|---:|
| Topic relevance | 0.35 |
| Learning level | 0.20 |
| Prerequisite compatibility | 0.15 |
| Resource quality | 0.15 |
| Learning objective | 0.10 |
| Freshness | 0.05 |

Weights must sum to 1.0.

### 6. RecommendationScoreBreakdown

Stores normalized scoring factor values.

Every component must be between 0 and 1.

### 7. RecommendationScoringResult

Represents a complete scoring result.

Includes:

- Resource ID
- Final score
- Scoring breakdown
- Applied weights
- Algorithm version

### 8. ScoredRecommendation

Represents a ranked recommendation with explanation.

### 9. RecommendationResponse

Defines the persisted recommendation response.

Includes:

- Recommendation ID
- Resource ID
- Type
- Score
- Rank
- Explanation
- Status
- Algorithm version
- Metadata
- Timestamps
- Resource details

### 10. RecommendationListResponse

Provides a structured collection of recommendation responses.

## Validation Rules

- Unknown request fields are rejected.
- User IDs cannot be supplied through generation requests.
- Recommendation scores must be normalized.
- Scoring weights must sum to 1.
- Ratings must be between 1 and 5.
- Resource duration cannot be negative.
- Resource quality must be between 0 and 5.
- Duplicate resource types are rejected.
- Duplicate recommendation ranks are rejected.

## Security

The authenticated user identity is obtained from
the authentication dependency.

The request schema does not allow a caller to choose
another user's identity.

## Database Compatibility

The response contracts correspond to the existing
Recommendation and StudyResource models.

No database migration is required for this subphase.

## Testing

Run:

pytest tests/schemas/test_recommendations.py -v

## Completion Criteria

- All recommendation domain contracts are implemented.
- Validation rules are enforced.
- Invalid inputs are rejected.
- Existing database field types are respected.
- Tests pass.
- Documentation is complete.