from enum import Enum

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)


class QueryIntent(str, Enum):
    ACADEMIC_LEARNING = "academic_learning"
    DOCUMENT_GROUNDED = "document_grounded"
    RESOURCE_DISCOVERY = "resource_discovery"
    RECOMMENDATION = "recommendation"
    STUDY_MATERIAL_GENERATION = "study_material_generation"
    CONVERSATION_FOLLOW_UP = "conversation_follow_up"
    UNKNOWN = "unknown"


class AcademicTaskType(str, Enum):
    EXPLANATION = "explanation"
    COMPARISON = "comparison"
    PROBLEM_SOLVING = "problem_solving"
    SUMMARIZATION = "summarization"
    QUESTION_GENERATION = "question_generation"
    DEFINITION = "definition"
    GENERAL = "general"


class ClassificationEvidence(BaseModel):
    """
    Explains which deterministic signals influenced
    the classification.
    """

    matched_patterns: list[str] = Field(
        default_factory=list
    )

    matched_keywords: list[str] = Field(
        default_factory=list
    )

    rules_applied: list[str] = Field(
        default_factory=list
    )


class QueryClassification(BaseModel):
    """
    Structured output of the deterministic query
    classification engine.

    Confidence is a heuristic ranking score,
    not a calibrated probability.
    """

    intent: QueryIntent

    task_type: AcademicTaskType

    confidence: float = Field(
        ge=0.0,
        le=1.0
    )

    suggested_workflow: str = Field(
        min_length=1,
        max_length=100
    )

    requires_conversation_context: bool = False

    requires_document_context: bool = False

    requires_external_resources: bool = False

    requires_personalization: bool = False

    ambiguous: bool = False

    evidence: ClassificationEvidence = Field(
        default_factory=ClassificationEvidence
    )

    classifier_version: str = "1.0.0"


class QueryClassificationRequest(BaseModel):
    """
    Input contract for query classification.
    """

    query: str = Field(
        min_length=1,
        max_length=5000
    )

    has_conversation_context: bool = False

    has_document_context: bool = False

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                "Query cannot be empty."
            )

        return value