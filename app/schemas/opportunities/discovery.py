from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.schemas.opportunities.opportunity import (
    OpportunityCreate,
    OpportunityType,
)


class OpportunityDiscoveryRequest(BaseModel):
    """
    Validated request for discovering external opportunities.

    This schema represents discovery inputs only.
    It does not perform ranking, deduplication or
    deadline eligibility evaluation.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    query: str = Field(
        min_length=1,
        max_length=500,
    )

    providers: list[str] | None = Field(
        default=None,
        max_length=20,
    )

    opportunity_types: list[OpportunityType] = Field(
        default_factory=list,
        max_length=8,
    )

    location: str | None = Field(
        default=None,
        max_length=255,
    )

    is_remote: bool | None = None

    limit_per_provider: int = Field(
        default=20,
        ge=1,
        le=100,
    )

    max_results: int = Field(
        default=100,
        ge=1,
        le=500,
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:

        value = value.strip()

        if not value:
            raise ValueError(
                "Discovery query cannot be empty."
            )

        return value

    @field_validator("location")
    @classmethod
    def validate_location(
        cls,
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        value = value.strip()

        return value or None

    @field_validator("providers")
    @classmethod
    def validate_providers(
        cls,
        value: list[str] | None,
    ) -> list[str] | None:

        if value is None:
            return None

        normalized = []
        seen = set()

        for provider in value:

            if not isinstance(provider, str):
                raise ValueError(
                    "Provider names must be strings."
                )

            provider = provider.strip().casefold()

            if not provider:
                raise ValueError(
                    "Provider names cannot be empty."
                )

            if provider not in seen:
                seen.add(provider)
                normalized.append(provider)

        if not normalized:
            raise ValueError(
                "At least one provider must be supplied "
                "when providers are explicitly specified."
            )

        return normalized

    @field_validator("opportunity_types")
    @classmethod
    def validate_opportunity_types(
        cls,
        value: list[OpportunityType],
    ) -> list[OpportunityType]:

        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def validate_result_limits(self):

        if self.max_results < 1:
            raise ValueError(
                "max_results must be positive."
            )

        return self


class OpportunityProviderFailure(BaseModel):
    """
    Sanitized information about a failed provider search.

    Raw exception messages are not returned to API consumers.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    provider: str

    error_type: str

    message: str


class OpportunityDiscoveryResponse(BaseModel):
    """
    Aggregated response from the opportunity discovery service.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    query: str

    total_results: int = Field(
        ge=0,
    )

    opportunities: list[OpportunityCreate]

    providers_requested: list[str] = Field(
        default_factory=list,
    )

    providers_searched: list[str] = Field(
        default_factory=list,
    )

    providers_failed: list[str] = Field(
        default_factory=list,
    )

    provider_failures: list[
        OpportunityProviderFailure
    ] = Field(
        default_factory=list,
    )

    retrieved_at: datetime

    @field_validator("retrieved_at")
    @classmethod
    def validate_retrieved_at(
        cls,
        value: datetime,
    ) -> datetime:

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "retrieved_at must be timezone-aware."
            )

        return value

    @model_validator(mode="after")
    def validate_result_count(self):

        if self.total_results != len(self.opportunities):
            raise ValueError(
                "total_results must equal the number "
                "of returned opportunities."
            )

        return self