from datetime import datetime
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from app.schemas.external_resources import (
    ExternalResourceType,
)


class EducationalResourceSearchArguments(BaseModel):

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    query: str = Field(
        min_length=2,
        max_length=2000,
    )

    providers: list[str] | None = Field(
        default=None,
        max_length=10,
    )

    resource_types: list[ExternalResourceType] = Field(
        default_factory=list,
        max_length=8,
    )

    subject: str | None = Field(
        default=None,
        max_length=100,
    )

    language: str | None = Field(
        default=None,
        max_length=30,
    )

    limit_per_provider: int = Field(
        default=10,
        ge=1,
        le=50,
    )


class EducationalResourceToolOutput(BaseModel):

    model_config = ConfigDict(
        extra="forbid",
    )

    query: str

    total_results: int = Field(
        ge=0,
    )

    resources: list[dict[str, Any]]

    providers_searched: list[str]

    providers_failed: list[str]

    retrieved_at: datetime


class EducationalResourceWorkflowInput(BaseModel):

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    query: str = Field(
        min_length=2,
        max_length=2000,
    )

    providers: list[str] | None = Field(
        default=None,
        max_length=10,
    )

    resource_types: list[ExternalResourceType] = Field(
        default_factory=list,
        max_length=8,
    )

    subject: str | None = Field(
        default=None,
        max_length=100,
    )

    language: str | None = Field(
        default=None,
        max_length=30,
    )

    limit_per_provider: int = Field(
        default=10,
        ge=1,
        le=50,
    )