from enum import Enum

from pydantic import BaseModel, Field, field_validator

from app.schemas.query_classification import QueryClassification


class RewriteStrategy(str, Enum):
    UNCHANGED = "unchanged"
    NORMALIZED = "normalized"
    CONTEXT_RESOLVED = "context_resolved"
    TASK_ENRICHED = "task_enriched"


class QueryRewriteRequest(BaseModel):
    """
    Input schema for intelligent query rewriting.
    """

    query: str = Field(
        min_length=1,
        max_length=5000,
    )

    conversation_context: str | None = Field(
        default=None,
        max_length=3000,
    )

    classification: QueryClassification | None = None

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Query cannot be empty.")

        return value

    @field_validator("conversation_context")
    @classmethod
    def validate_conversation_context(
        cls,
        value: str | None,
    ) -> str | None:
        if value is not None:
            value = value.strip()

            if not value:
                return None

        return value


class QueryRewriteResult(BaseModel):
    """
    Structured result of query rewriting.
    """

    original_query: str = Field(
        min_length=1,
        max_length=5000,
    )

    normalized_query: str = Field(
        min_length=1,
        max_length=5000,
    )

    standalone_query: str = Field(
        min_length=1,
        max_length=5000,
    )

    retrieval_query: str = Field(
        min_length=1,
        max_length=5000,
    )

    search_queries: list[str] = Field(
        default_factory=list,
        max_length=3,
    )

    strategy: RewriteStrategy

    rewritten: bool

    context_used: bool = False

    reason: str = Field(
        min_length=1,
        max_length=300,
    )

    classifier_version: str = "1.0.0"

    @field_validator("search_queries")
    @classmethod
    def validate_search_queries(
        cls,
        value: list[str],
    ) -> list[str]:
        cleaned_queries = []

        for query in value:
            query = query.strip()

            if not query:
                raise ValueError(
                    "Search queries cannot contain empty strings."
                )

            cleaned_queries.append(query)

        return cleaned_queries