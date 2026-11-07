from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.schemas.external_resources import (
    ExternalResourceType,
)


class ResourceDiscoveryRequest(BaseModel):
    """
    Validated request for searching external educational
    resources across configured providers.
    """

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

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:

        value = value.strip()

        if not value:
            raise ValueError(
                "Search query cannot be empty."
            )

        if len(value) < 2:
            raise ValueError(
                "Search query must contain at least "
                "two characters."
            )

        return value

    @field_validator("providers")
    @classmethod
    def validate_providers(cls, value):

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
                "when providers is specified."
            )

        return normalized

    @field_validator("subject", "language")
    @classmethod
    def normalize_optional_filters(cls, value):

        if value is None:
            return None

        value = value.strip()

        return value or None