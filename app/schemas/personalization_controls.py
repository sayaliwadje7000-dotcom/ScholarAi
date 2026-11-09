from pydantic import BaseModel, ConfigDict, Field, field_validator


class PersonalizationControlsUpdate(BaseModel):
    """
    Student-controlled learning preferences.

    Only fields already supported by UserPreferences
    are exposed in this phase.
    """

    preferred_language: str | None = Field(
        default=None,
        max_length=10,
    )

    education_level: str | None = Field(
        default=None,
        max_length=50,
    )

    preferred_subjects: list[str] | None = Field(
        default=None,
        max_length=30,
    )

    notification_enabled: bool | None = None

    @field_validator("preferred_language", "education_level")
    @classmethod
    def normalize_optional_strings(cls, value):
        if value is None:
            return None

        value = value.strip()

        return value or None

    @field_validator("preferred_subjects")
    @classmethod
    def normalize_subjects(cls, subjects):
        if subjects is None:
            return None

        normalized = []
        seen = set()

        for subject in subjects:
            if not isinstance(subject, str):
                raise ValueError(
                    "Every subject must be a string."
                )

            subject = subject.strip()

            if not subject:
                raise ValueError(
                    "Subjects cannot contain empty values."
                )

            key = subject.casefold()

            if key not in seen:
                normalized.append(subject)
                seen.add(key)

        return normalized


class PersonalizationControlsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    preferred_language: str | None
    education_level: str | None
    preferred_subjects: list[str]
    notification_enabled: bool


class PersonalizationControlsResetResponse(BaseModel):
    message: str
    controls: PersonalizationControlsResponse