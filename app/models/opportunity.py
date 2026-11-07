
import uuid

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)

from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Opportunity(Base):
    """
    Represents an external academic or professional opportunity
    discovered by ScholarAI.

    Examples:
    - Hackathons
    - Internships
    - Competitions
    - Workshops
    - Conferences
    - Academic events
    - Scholarships
    """

    __tablename__ = "opportunities"

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "external_id",
            name="uq_opportunities_provider_external_id",
        ),

        CheckConstraint(
            "length(trim(title)) > 0",
            name="ck_opportunities_title_nonempty",
        ),

        CheckConstraint(
            "length(trim(provider)) > 0",
            name="ck_opportunities_provider_nonempty",
        ),

        CheckConstraint(
            """
            opportunity_type IN (
                'hackathon',
                'internship',
                'competition',
                'workshop',
                'conference',
                'academic_event',
                'scholarship',
                'other'
            )
            """,
            name="ck_opportunities_valid_type",
        ),

        CheckConstraint(
            """
            status IN (
                'discovered',
                'unknown',
                'upcoming',
                'open',
                'closed',
                'expired',
                'cancelled'
            )
            """,
            name="ck_opportunities_valid_status",
        ),

        CheckConstraint(
            """
            registration_start IS NULL
            OR registration_deadline IS NULL
            OR registration_start <= registration_deadline
            """,
            name="ck_opportunities_valid_registration_dates",
        ),

        CheckConstraint(
            """
            event_start IS NULL
            OR event_end IS NULL
            OR event_start <= event_end
            """,
            name="ck_opportunities_valid_event_dates",
        ),

        CheckConstraint(
            "retrieval_count >= 0",
            name="ck_opportunities_nonnegative_retrieval_count",
        ),

        CheckConstraint(
            "jsonb_typeof(eligibility) = 'object'",
            name="ck_opportunities_eligibility_object",
        ),

        CheckConstraint(
            "jsonb_typeof(required_skills) = 'array'",
            name="ck_opportunities_required_skills_array",
        ),

        CheckConstraint(
            "jsonb_typeof(metadata) = 'object'",
            name="ck_opportunities_metadata_object",
        ),

        Index(
            "ix_opportunities_provider",
            "provider",
        ),

        Index(
            "ix_opportunities_type",
            "opportunity_type",
        ),

        Index(
            "ix_opportunities_status",
            "status",
        ),

        Index(
            "ix_opportunities_registration_deadline",
            "registration_deadline",
        ),

        Index(
            "ix_opportunities_event_start",
            "event_start",
        ),

        Index(
            "ix_opportunities_type_status_deadline",
            "opportunity_type",
            "status",
            "registration_deadline",
        ),
    )

    # PRIMARY KEY

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # EXTERNAL PROVIDER IDENTITY

    provider: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    external_id: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # BASIC INFORMATION

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    opportunity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="other",
        server_default=text("'other'"),
    )

    organizer: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # SOURCE INFORMATION

    official_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )

    source_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )

    application_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )

    # ELIGIBILITY

    eligibility: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSONB),
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    required_skills: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(JSONB),
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )

    # LOCATION

    location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    is_remote: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    # REGISTRATION DATES

    registration_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    registration_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # EVENT DATES

    event_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    event_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # OPPORTUNITY STATUS

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="discovered",
        server_default=text("'discovered'"),
    )

    verification_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="unverified",
        server_default=text("'unverified'"),
    )

    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    # SOURCE TIMESTAMPS

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # FLEXIBLE PROVIDER METADATA
    #
    # The database column is named "metadata".
    # The Python attribute is "opportunity_metadata".
    # This avoids overriding SQLAlchemy's Base.metadata.

    opportunity_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        MutableDict.as_mutable(JSONB),
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    # SOURCE RETRIEVAL TRACKING

    retrieval_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )

    # INTERNAL TIMESTAMPS

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # INITIALIZATION

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())

        kwargs.setdefault("opportunity_type", "other")
        kwargs.setdefault("status", "discovered")
        kwargs.setdefault("verification_status", "unverified")

        kwargs.setdefault("eligibility", {})
        kwargs.setdefault("required_skills", [])
        kwargs.setdefault("opportunity_metadata", {})

        kwargs.setdefault("is_active", True)
        kwargs.setdefault("is_remote", False)
        kwargs.setdefault("retrieval_count", 1)

        # The domain schema accepts eligibility as a string.
        # The database stores eligibility as a JSON object.
        eligibility = kwargs.get("eligibility")

        if isinstance(eligibility, str):
            kwargs["eligibility"] = (
                {"description": eligibility}
                if eligibility.strip()
                else {}
            )

        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return (
            f"<Opportunity("
            f"id={self.id}, "
            f"title={self.title!r}, "
            f"type={self.opportunity_type!r}, "
            f"provider={self.provider!r})>"
        )
