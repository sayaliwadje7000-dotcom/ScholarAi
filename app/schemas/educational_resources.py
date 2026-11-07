from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.schemas.external_resources import (
    ExternalAccessType,
    ExternalResource,
    ExternalResourceType,
)


class EducationalResourceBase(BaseModel):
    """
    Common validated representation of an external
    educational resource.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    provider: str = Field(
        min_length=1,
        max_length=150,
    )

    external_id: str = Field(
        min_length=1,
        max_length=500,
    )

    title: str = Field(
        min_length=1,
        max_length=255,
    )

    canonical_url: str = Field(
        min_length=1,
        max_length=2048,
    )

    resource_type: ExternalResourceType

    description: str | None = Field(
        default=None,
        max_length=20000,
    )

    authors: tuple[str, ...] = Field(
        default_factory=tuple,
        max_length=100,
    )

    subject: str | None = Field(
        default=None,
        max_length=100,
    )

    language: str | None = Field(
        default=None,
        max_length=30,
    )

    published_at: datetime | None = None

    retrieved_at: datetime

    license: str | None = Field(
        default=None,
        max_length=500,
    )

    access_type: ExternalAccessType

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )

    @field_validator(
        "provider",
        "external_id",
        "title",
    )
    @classmethod
    def validate_required_strings(cls, value: str) -> str:

        value = value.strip()

        if not value:
            raise ValueError(
                "This field cannot contain only whitespace."
            )

        return value

    @field_validator("canonical_url")
    @classmethod
    def validate_canonical_url(cls, value: str) -> str:

        value = value.strip()

        parsed = urlparse(value)

        if parsed.scheme not in {"http", "https"}:
            raise ValueError(
                "Resource URL must use HTTP or HTTPS."
            )

        if not parsed.hostname:
            raise ValueError(
                "Resource URL must contain a hostname."
            )

        if parsed.username or parsed.password:
            raise ValueError(
                "Resource URLs cannot contain credentials."
            )

        return value

    @field_validator("authors")
    @classmethod
    def validate_authors(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:

        normalized = []

        seen = set()

        for author in value:

            if not isinstance(author, str):
                raise ValueError(
                    "Every author must be a string."
                )

            author = author.strip()

            if not author:
                continue

            key = author.casefold()

            if key not in seen:

                seen.add(key)

                normalized.append(author)

        return tuple(normalized)

    @field_validator("published_at", "retrieved_at")
    @classmethod
    def validate_timezone_aware_dates(
        cls,
        value: datetime | None,
    ) -> datetime | None:

        if value is None:
            return None

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "Datetime values must be timezone-aware."
            )

        return value

    @model_validator(mode="after")
    def validate_metadata(self):

        if not isinstance(self.metadata, dict):
            raise ValueError(
                "Resource metadata must be a dictionary."
            )

        return self


class EducationalResourceResponse(
    EducationalResourceBase
):
    """
    External resource representation returned to
    application consumers.
    """

    @classmethod
    def from_external_resource(
        cls,
        resource: ExternalResource,
    ) -> "EducationalResourceResponse":

        return cls(
            provider=resource.provider,
            external_id=resource.external_id,
            title=resource.title,
            canonical_url=resource.canonical_url,
            resource_type=resource.resource_type,
            description=resource.description,
            authors=resource.authors,
            subject=resource.subject,
            language=resource.language,
            published_at=resource.published_at,
            retrieved_at=resource.retrieved_at,
            license=resource.license,
            access_type=resource.access_type,
            metadata=resource.metadata,
        )


class EducationalResourceListResponse(BaseModel):
    """
    Standardized response containing external resources.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    query: str = Field(
        min_length=1,
        max_length=2000,
    )

    total_results: int = Field(
        ge=0,
    )

    resources: list[EducationalResourceResponse]

    providers_searched: list[str] = Field(
        default_factory=list,
    )

    providers_failed: list[str] = Field(
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
                "Retrieved timestamp must be timezone-aware."
            )

        return value

    @model_validator(mode="after")
    def validate_result_count(self):

        if self.total_results != len(self.resources):
            raise ValueError(
                "total_results must match the number "
                "of resources returned."
            )

        return self