from datetime import datetime, timezone
from enum import Enum
from typing import Any
from urllib.parse import urlparse

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


# ============================================================
# ENUMERATIONS
# ============================================================

class OpportunityType(str, Enum):
    HACKATHON = "hackathon"
    INTERNSHIP = "internship"
    COMPETITION = "competition"
    WORKSHOP = "workshop"
    CONFERENCE = "conference"
    ACADEMIC_EVENT = "academic_event"
    SCHOLARSHIP = "scholarship"
    OTHER = "other"


class OpportunityStatus(str, Enum):
    DISCOVERED = "discovered"
    UPCOMING = "upcoming"
    OPEN = "open"
    CLOSED = "closed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class OpportunityVerificationStatus(str, Enum):
    OFFICIAL_VERIFIED = "official_verified"
    SECONDARY_VERIFIED = "secondary_verified"
    UNVERIFIED = "unverified"
    CONFLICTING = "conflicting"
    UNAVAILABLE = "unavailable"


# ============================================================
# BASE SCHEMA
# ============================================================

class OpportunityBase(BaseModel):

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        populate_by_name=True,
    )

    provider: str = Field(
        min_length=1,
        max_length=100,
    )

    external_id: str | None = Field(
        default=None,
        max_length=500,
    )

    title: str = Field(
        min_length=1,
        max_length=500,
    )

    description: str | None = None

    opportunity_type: OpportunityType = OpportunityType.OTHER

    organizer: str | None = Field(
        default=None,
        max_length=255,
    )

    official_url: str | None = Field(
        default=None,
        max_length=2048,
    )

    source_url: str | None = Field(
        default=None,
        max_length=2048,
    )

    application_url: str | None = Field(
        default=None,
        max_length=2048,
    )

    eligibility: dict[str, Any] | str | None = None

    required_skills: list[str] = Field(
        default_factory=list,
        max_length=100,
    )

    location: str | None = Field(
        default=None,
        max_length=255,
    )

    is_remote: bool = False

    registration_start: datetime | None = None

    registration_deadline: datetime | None = None

    event_start: datetime | None = None

    event_end: datetime | None = None

    status: OpportunityStatus = OpportunityStatus.DISCOVERED

    verification_status: OpportunityVerificationStatus = (
        OpportunityVerificationStatus.UNVERIFIED
    )

    is_active: bool = True

    published_at: datetime | None = None

    retrieved_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    last_verified_at: datetime | None = None

    opportunity_metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices(
            "opportunity_metadata",
            "metadata",
        ),
        serialization_alias="metadata",
    )

    # --------------------------------------------------------
    # METADATA COMPATIBILITY PROPERTY
    # --------------------------------------------------------

    @property
    def metadata(self) -> dict[str, Any]:
        return self.opportunity_metadata

    # --------------------------------------------------------
    # ELIGIBILITY VALIDATION
    # --------------------------------------------------------

    @field_validator("eligibility")
    @classmethod
    def normalize_eligibility(cls, value):

        if isinstance(value, str):
            value = value.strip()

            if not value:
                return None

            return {"description": value}

        return value

    # --------------------------------------------------------
    # REQUIRED STRING VALIDATION
    # --------------------------------------------------------

    @field_validator("provider", "title")
    @classmethod
    def validate_required_strings(cls, value: str):

        value = value.strip()

        if not value:
            raise ValueError(
                "This field cannot contain only whitespace."
            )

        return value

    # --------------------------------------------------------
    # OPTIONAL STRING VALIDATION
    # --------------------------------------------------------

    @field_validator(
        "external_id",
        "organizer",
        "location",
    )
    @classmethod
    def normalize_optional_strings(cls, value):

        if value is None:
            return None

        value = value.strip()

        return value or None

    # --------------------------------------------------------
    # URL VALIDATION
    # --------------------------------------------------------

    @field_validator(
        "official_url",
        "source_url",
        "application_url",
        mode="before",
    )
    @classmethod
    def validate_urls(cls, value):

        if value is None:
            return None

        if isinstance(value, str):
            value = value.strip()

            if not value:
                return None

        parsed = urlparse(value)

        if parsed.scheme not in {"http", "https"}:
            raise ValueError(
                "URL must use HTTP or HTTPS."
            )

        if not parsed.hostname:
            raise ValueError(
                "URL must contain a valid hostname."
            )

        if parsed.username or parsed.password:
            raise ValueError(
                "URL cannot contain embedded credentials."
            )

        return value

    # --------------------------------------------------------
    # SKILLS VALIDATION
    # --------------------------------------------------------

    @field_validator("required_skills")
    @classmethod
    def validate_required_skills(cls, value):

        normalized = []
        seen = set()

        for skill in value:

            if not isinstance(skill, str):
                raise ValueError(
                    "Every required skill must be a string."
                )

            skill = skill.strip()

            if not skill:
                continue

            key = skill.casefold()

            if key not in seen:
                seen.add(key)
                normalized.append(skill)

        return normalized

    # --------------------------------------------------------
    # DATETIME VALIDATION
    # --------------------------------------------------------

    @field_validator(
        "registration_start",
        "registration_deadline",
        "event_start",
        "event_end",
        "published_at",
        "retrieved_at",
        "last_verified_at",
    )
    @classmethod
    def validate_timezone_aware_dates(cls, value):

        if value is None:
            return None

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "Datetime values must be timezone-aware."
            )

        return value

    # --------------------------------------------------------
    # DATE CONSISTENCY
    # --------------------------------------------------------

    @model_validator(mode="after")
    def validate_date_ranges(self):

        if (
            self.registration_start is not None
            and self.registration_deadline is not None
            and self.registration_start > self.registration_deadline
        ):
            raise ValueError(
                "Registration start cannot be after "
                "registration deadline."
            )

        if (
            self.event_start is not None
            and self.event_end is not None
            and self.event_start > self.event_end
        ):
            raise ValueError(
                "Event start cannot be after event end."
            )

        return self


# ============================================================
# CREATE SCHEMA
# ============================================================

class OpportunityCreate(OpportunityBase):
    """Validated input for creating an opportunity."""

    pass


# ============================================================
# RESPONSE SCHEMA
# ============================================================

class OpportunityResponse(OpportunityBase):
    """Opportunity returned by ScholarAI."""

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        populate_by_name=True,
    )

    id: str | None = None

    retrieval_count: int = Field(
        default=1,
        ge=0,
    )

    created_at: datetime | None = None

    updated_at: datetime | None = None


# ============================================================
# LIST RESPONSE
# ============================================================

class OpportunityListResponse(BaseModel):

    model_config = ConfigDict(
        extra="forbid",
    )

    query: str = "opportunity_search"

    total_results: int = Field(
        ge=1,
    )

    opportunities: list[OpportunityResponse]

    providers_searched: list[str] = Field(
        default_factory=list,
    )

    providers_failed: list[str] = Field(
        default_factory=list,
    )

    retrieved_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @field_validator("retrieved_at")
    @classmethod
    def validate_retrieved_at(cls, value):

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "Retrieved timestamp must be timezone-aware."
            )

        return value

    @model_validator(mode="after")
    def validate_result_count(self):

        if self.total_results != len(self.opportunities):
            raise ValueError(
                "total_results must match the number "
                "of opportunities returned."
            )

        return self