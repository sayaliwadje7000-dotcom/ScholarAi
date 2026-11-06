from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


# ============================================================
# ENUMS
# ============================================================


class RecommendationType(str, Enum):
    PERSONALIZED = "personalized"
    TRENDING = "trending"
    RELATED = "related"
    POPULAR = "popular"
    CONTINUE_LEARNING = "continue_learning"


class ResourceType(str, Enum):
    VIDEO = "video"
    ARTICLE = "article"
    NOTES = "notes"
    COURSE = "course"
    DOCUMENTATION = "documentation"
    TUTORIAL = "tutorial"
    WEBSITE = "website"
    BOOK = "book"


class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class RecommendationStatus(str, Enum):
    GENERATED = "generated"
    PRESENTED = "presented"
    CLICKED = "clicked"
    DISMISSED = "dismissed"
    EXPIRED = "expired"


class InteractionType(str, Enum):
    VIEW = "view"
    CLICK = "click"
    SAVE = "save"
    RATE = "rate"
    COMPLETE = "complete"


# ============================================================
# BASE SCHEMA
# ============================================================


class RecommendationBaseSchema(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


# ============================================================
# RECOMMENDATION GENERATION REQUEST
# ============================================================


class RecommendationRequest(RecommendationBaseSchema):
    """
    Public request schema for generating recommendations.

    User identity is deliberately excluded.
    The authenticated user must be obtained from
    the authentication dependency.
    """

    query: str | None = Field(
        default=None,
        min_length=1,
        max_length=1000,
        description="Optional topic or learning query.",
    )

    subject: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    resource_types: list[ResourceType] | None = Field(
        default=None,
        min_length=1,
        max_length=8,
    )

    difficulty_level: DifficultyLevel | None = None

    language: str | None = Field(
        default=None,
        min_length=2,
        max_length=30,
    )

    recommendation_type: RecommendationType = Field(
        default=RecommendationType.PERSONALIZED,
    )

    limit: int = Field(
        default=10,
        ge=1,
        le=50,
    )

    exclude_completed: bool = Field(
        default=True,
    )

    @field_validator("query", "subject", "language")
    @classmethod
    def normalize_optional_strings(
        cls,
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        value = value.strip()

        if not value:
            raise ValueError(
                "Value cannot contain only whitespace."
            )

        return value

    @field_validator("resource_types")
    @classmethod
    def validate_resource_types(
        cls,
        value: list[ResourceType] | None,
    ) -> list[ResourceType] | None:

        if value is None:
            return None

        if len(value) != len(set(value)):
            raise ValueError(
                "Duplicate resource types are not allowed."
            )

        return value

    @field_validator("language")
    @classmethod
    def normalize_language(
        cls,
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        return value.lower()


# ============================================================
# USER LEARNING CONTEXT
# ============================================================


class InteractionSummary(RecommendationBaseSchema):
    """
    Internal summary of a user's resource interactions.
    """

    resource_id: UUID

    interaction_type: InteractionType

    rating: int | None = Field(
        default=None,
        ge=1,
        le=5,
    )

    duration_seconds: int | None = Field(
        default=None,
        ge=0,
    )

    occurred_at: datetime

    @model_validator(mode="after")
    def validate_rating(self):

        if self.interaction_type == InteractionType.RATE:
            if self.rating is None:
                raise ValueError(
                    "Rating is required for rate interactions."
                )

        elif self.rating is not None:
            raise ValueError(
                "Rating is only permitted for rate interactions."
            )

        return self


class LearningContext(RecommendationBaseSchema):
    """
    Internal representation of the authenticated user's
    learning preferences and interaction history.
    """

    user_id: UUID

    preferred_language: str | None = None

    education_level: str | None = None

    preferred_subjects: list[str] = Field(
        default_factory=list,
        max_length=50,
    )

    learning_goals: list[str] = Field(
        default_factory=list,
        max_length=50,
    )

    recent_interactions: list[InteractionSummary] = Field(
        default_factory=list,
        max_length=500,
    )

    @field_validator(
        "preferred_subjects",
        "learning_goals",
    )
    @classmethod
    def normalize_string_lists(
        cls,
        values: list[str],
    ) -> list[str]:

        normalized = []

        for value in values:

            value = value.strip()

            if not value:
                raise ValueError(
                    "List values cannot be empty."
                )

            normalized.append(value)

        return list(dict.fromkeys(normalized))


# ============================================================
# RESOURCE CANDIDATE
# ============================================================


class RecommendationCandidate(RecommendationBaseSchema):
    """
    Normalized resource representation used internally
    by recommendation services.
    """

    resource_id: UUID

    title: str = Field(
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    resource_type: ResourceType

    url: str = Field(
        min_length=1,
        max_length=2048,
    )

    provider: str | None = None

    subject: str | None = None

    language: str | None = None

    difficulty_level: DifficultyLevel | None = None

    estimated_duration_minutes: int | None = Field(
        default=None,
        ge=0,
    )

    quality_score: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("5"),
        max_digits=4,
        decimal_places=2,
    )

    category_slugs: list[str] = Field(
        default_factory=list,
        max_length=100,
    )

    published_at: datetime | None = None

    is_active: bool

    @field_validator("title", "url")
    @classmethod
    def validate_required_strings(
        cls,
        value: str,
    ) -> str:

        value = value.strip()

        if not value:
            raise ValueError(
                "Value cannot be empty."
            )

        return value

    @field_validator("category_slugs")
    @classmethod
    def normalize_categories(
        cls,
        values: list[str],
    ) -> list[str]:

        normalized = [
            value.strip().lower()
            for value in values
            if value.strip()
        ]

        return list(dict.fromkeys(normalized))


# ============================================================
# SCORING WEIGHTS
# ============================================================


class RecommendationWeights(RecommendationBaseSchema):
    """
    Configurable weights for the rule-based scoring engine.
    """

    topic_relevance: float = Field(
        default=0.35,
        ge=0,
        le=1,
    )

    learning_level: float = Field(
        default=0.20,
        ge=0,
        le=1,
    )

    prerequisite_compatibility: float = Field(
        default=0.15,
        ge=0,
        le=1,
    )

    resource_quality: float = Field(
        default=0.15,
        ge=0,
        le=1,
    )

    learning_objective: float = Field(
        default=0.10,
        ge=0,
        le=1,
    )

    freshness: float = Field(
        default=0.05,
        ge=0,
        le=1,
    )

    @model_validator(mode="after")
    def validate_weight_total(self):

        total = sum(
            (
                self.topic_relevance,
                self.learning_level,
                self.prerequisite_compatibility,
                self.resource_quality,
                self.learning_objective,
                self.freshness,
            )
        )

        if abs(total - 1.0) > 1e-9:
            raise ValueError(
                "Recommendation weights must sum to 1.0."
            )

        return self


# ============================================================
# SCORING BREAKDOWN
# ============================================================


class RecommendationScoreBreakdown(
    RecommendationBaseSchema
):
    """
    Individual normalized scoring components.

    These values represent actual scoring results,
    not the configured weights.
    """

    topic_relevance: float = Field(
        ge=0,
        le=1,
    )

    learning_level: float = Field(
        ge=0,
        le=1,
    )

    prerequisite_compatibility: float = Field(
        ge=0,
        le=1,
    )

    resource_quality: float = Field(
        ge=0,
        le=1,
    )

    learning_objective: float = Field(
        ge=0,
        le=1,
    )

    freshness: float = Field(
        ge=0,
        le=1,
    )


class RecommendationScoringResult(
    RecommendationBaseSchema
):
    """
    Complete scoring output for an individual resource.
    """

    resource_id: UUID

    score: float = Field(
        ge=0,
        le=1,
    )

    breakdown: RecommendationScoreBreakdown

    weights: RecommendationWeights

    algorithm_version: str = Field(
        min_length=1,
        max_length=50,
    )


# ============================================================
# SCORED RECOMMENDATION
# ============================================================


class ScoredRecommendation(RecommendationBaseSchema):
    """
    Internal recommendation result after scoring and ranking.
    """

    resource: RecommendationCandidate

    score: float = Field(
        ge=0,
        le=1,
    )

    rank_position: int = Field(
        ge=1,
    )

    reason: str = Field(
        min_length=1,
        max_length=2000,
    )

    breakdown: RecommendationScoreBreakdown

    recommendation_type: RecommendationType

    algorithm_version: str = Field(
        min_length=1,
        max_length=50,
    )


# ============================================================
# RECOMMENDATION RESPONSE
# ============================================================


class RecommendedResourceResponse(
    RecommendationBaseSchema
):
    """
    Resource information exposed in recommendation responses.
    """

    id: UUID

    title: str

    description: str | None = None

    resource_type: ResourceType

    url: str

    provider: str | None = None

    subject: str | None = None

    language: str | None = None

    difficulty_level: DifficultyLevel | None = None

    estimated_duration_minutes: int | None = None

    quality_score: Decimal | None = None


class RecommendationResponse(
    RecommendationBaseSchema
):
    """
    Persisted recommendation response.
    """

    id: UUID

    resource_id: UUID

    recommendation_type: RecommendationType

    score: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("1"),
        max_digits=5,
        decimal_places=4,
    )

    rank_position: int = Field(
        ge=1,
    )

    reason: str = Field(
        min_length=1,
    )

    status: RecommendationStatus

    algorithm_version: str

    recommendation_metadata: dict = Field(
        default_factory=dict,
    )

    generated_at: datetime

    expires_at: datetime | None = None

    resource: RecommendedResourceResponse

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        from_attributes=True,
    )

    @model_validator(mode="after")
    def validate_resource_relationship(self):

        if self.resource_id != self.resource.id:
            raise ValueError(
                "Recommendation resource ID must match "
                "the nested resource ID."
            )

        return self


# ============================================================
# RECOMMENDATION LIST RESPONSE
# ============================================================


class RecommendationListResponse(
    RecommendationBaseSchema
):
    """
    Paginated-style recommendation response.

    Pagination metadata is kept explicit so that
    cursor-based pagination can be introduced later.
    """

    recommendations: list[RecommendationResponse]

    total_results: int = Field(
        ge=0,
    )

    algorithm_version: str

    @model_validator(mode="after")
    def validate_result_count(self):

        if self.total_results != len(self.recommendations):
            raise ValueError(
                "total_results must equal the number "
                "of returned recommendations."
            )

        ranks = [
            recommendation.rank_position
            for recommendation in self.recommendations
        ]

        if len(ranks) != len(set(ranks)):
            raise ValueError(
                "Recommendation ranks must be unique."
            )

        return self