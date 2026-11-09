from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class ResponseFormat(str, Enum):

    PLAIN_TEXT = "plain_text"

    ACADEMIC = "academic"

    SUMMARY = "summary"

    COMPARISON = "comparison"

    STEP_BY_STEP = "step_by_step"


class ResponseValidationStatus(str, Enum):

    VALID = "valid"

    INVALID = "invalid"

    PARTIALLY_VALID = "partially_valid"


class AcademicStructuredResponse(BaseModel):

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    answer: str = Field(
        min_length=1,
        max_length=30000,
    )

    key_points: list[str] = Field(
        default_factory=list,
        max_length=20,
    )

    examples: list[str] = Field(
        default_factory=list,
        max_length=10,
    )

    caveats: list[str] = Field(
        default_factory=list,
        max_length=10,
    )

    conclusion: str | None = Field(
        default=None,
        max_length=5000,
    )

    @field_validator(
        "answer",
        "conclusion",
    )
    @classmethod
    def validate_optional_text(cls, value):

        if value is not None and not value.strip():

            raise ValueError(
                "Text fields cannot contain only whitespace."
            )

        return value

    @field_validator(
        "key_points",
        "examples",
        "caveats",
    )
    @classmethod
    def validate_text_lists(cls, values):

        cleaned = []

        for item in values:

            item = item.strip()

            if not item:

                raise ValueError(
                    "List items cannot be empty."
                )

            cleaned.append(item)

        return cleaned


class ResponseIntelligenceRequest(BaseModel):

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    response: str = Field(
        min_length=1,
        max_length=50000,
    )

    response_format: ResponseFormat = (
        ResponseFormat.PLAIN_TEXT
    )

    validate_safety: bool = True

    @field_validator("response")
    @classmethod
    def validate_response(cls, value):

        if not value.strip():

            raise ValueError(
                "Generated response cannot be empty."
            )

        return value


class ResponseIntelligenceResult(BaseModel):

    model_config = ConfigDict(
        extra="forbid",
    )

    response: str

    response_format: ResponseFormat

    validation_status: ResponseValidationStatus

    structured_response: AcademicStructuredResponse | None = None

    quality_issues: list[str] = Field(
        default_factory=list,
    )

    safety_validated: bool

    character_count: int = Field(
        ge=0,
    )

    word_count: int = Field(
        ge=0,
    )