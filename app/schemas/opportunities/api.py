from datetime import datetime
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class OpportunityStudentProfile(BaseModel):
    """
    Optional student information used for opportunity
    relevance and eligibility evaluation.

    Authentication and persistent student profiles
    will be integrated in Phase 18.
    """

    model_config = ConfigDict(extra="forbid")

    skills: list[str] = Field(default_factory=list)

    interests: list[str] = Field(default_factory=list)

    opportunity_types: list[str] = Field(
        default_factory=list
    )

    academic_year: str | int | None = None

    location: str | None = None

    preferred_locations: list[str] = Field(
        default_factory=list
    )

    is_remote_preferred: bool | None = None

    @field_validator(
        "skills",
        "interests",
        "opportunity_types",
        "preferred_locations",
    )
    @classmethod
    def validate_string_lists(cls, values):
        normalized = []

        for value in values:

            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    "Profile list values must be non-empty strings."
                )

            normalized.append(value.strip())

        return normalized


class OpportunityDiscoveryAPIRequest(BaseModel):
    """
    Public API request wrapping the existing discovery
    request and optional student personalization data.
    """

    model_config = ConfigDict(extra="forbid")

    query: str = Field(
        min_length=1,
        max_length=300,
    )

    providers: list[str] | None = None

    opportunity_types: list[str] = Field(
        default_factory=list
    )

    location: str | None = None

    is_remote: bool | None = None

    limit_per_provider: int = Field(
        default=20,
        ge=1,
        le=100,
    )

    max_results: int = Field(
        default=50,
        ge=1,
        le=100,
    )

    ranking_limit: int = Field(
        default=20,
        ge=1,
        le=100,
    )

    student_profile: OpportunityStudentProfile | None = None

    @field_validator("query")
    @classmethod
    def validate_query(cls, value):

        value = value.strip()

        if not value:
            raise ValueError(
                "Search query cannot be empty."
            )

        return value

    @field_validator("providers")
    @classmethod
    def validate_providers(cls, values):

        if values is None:
            return values

        normalized = []

        for provider in values:

            if not isinstance(provider, str) or not provider.strip():
                raise ValueError(
                    "Provider names must be non-empty strings."
                )

            provider = provider.strip().casefold()

            if provider not in normalized:
                normalized.append(provider)

        return normalized


class OpportunityProviderFailureResponse(BaseModel):

    provider: str

    error_type: str

    message: str


class OpportunityRankedItemResponse(BaseModel):

    opportunity: dict[str, Any]

    quality_score: float

    relevance_score: float

    final_score: float

    rank: int

    eligibility_status: str

    deadline_status: str

    freshness_status: str

    requires_refresh: bool

    explanations: list[str]


class OpportunityDiscoveryAPIResponse(BaseModel):
    """
    Complete response from the opportunity discovery
    and recommendation pipeline.
    """

    query: str

    total_received: int

    total_ranked: int

    total_excluded: int

    exclusion_reasons: dict[str, int]

    providers_requested: list[str]

    providers_searched: list[str]

    providers_failed: list[str]

    provider_failures: list[
        OpportunityProviderFailureResponse
    ]

    opportunities: list[
        OpportunityRankedItemResponse
    ]

    retrieved_at: datetime


class OpportunityCategoriesResponse(BaseModel):

    categories: list[str]