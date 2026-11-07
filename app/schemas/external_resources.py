from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ExternalResourceType(str, Enum):

    VIDEO = "video"
    ARTICLE = "article"
    COURSE = "course"
    DOCUMENTATION = "documentation"
    TUTORIAL = "tutorial"
    WEBSITE = "website"
    BOOK = "book"


class ExternalAccessType(str, Enum):

    OPEN_ACCESS = "open_access"
    PUBLIC = "public"
    PREVIEW = "preview"
    RESTRICTED = "restricted"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ExternalResource:

    provider: str

    external_id: str

    title: str

    canonical_url: str

    resource_type: ExternalResourceType

    description: str | None = None

    authors: tuple[str, ...] = ()

    subject: str | None = None

    language: str | None = None

    published_at: datetime | None = None

    retrieved_at: datetime = field(
        default_factory=datetime.utcnow
    )

    license: str | None = None

    access_type: ExternalAccessType = (
        ExternalAccessType.UNKNOWN
    )

    metadata: dict = field(default_factory=dict)

    def __post_init__(self):

        required_strings = {
            "provider": self.provider,
            "external_id": self.external_id,
            "title": self.title,
            "canonical_url": self.canonical_url,
        }

        for field_name, value in required_strings.items():

            if not isinstance(value, str) or not value.strip():

                raise ValueError(
                    f"{field_name} must be a non-empty string."
                )

        if not isinstance(
            self.resource_type,
            ExternalResourceType,
        ):
            raise TypeError(
                "Invalid external resource type."
            )

        if not isinstance(
            self.access_type,
            ExternalAccessType,
        ):
            raise TypeError(
                "Invalid external access type."
            )

        if not isinstance(self.authors, tuple):
            raise TypeError(
                "authors must be a tuple."
            )

        if not all(
            isinstance(author, str) and author.strip()
            for author in self.authors
        ):
            raise ValueError(
                "Every author must be a non-empty string."
            )

        if not isinstance(self.metadata, dict):
            raise TypeError(
                "metadata must be a dictionary."
            )

        if self.published_at is not None:

            if not isinstance(
                self.published_at,
                datetime,
            ):
                raise TypeError(
                    "published_at must be a datetime."
                )