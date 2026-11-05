from __future__ import annotations

import uuid

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class RetrievalRequest(BaseModel):
    """
    Request schema for semantic document retrieval.
    """

    model_config = ConfigDict(extra="forbid")

    query: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Natural language query for semantic retrieval.",
    )

    document_id: uuid.UUID | None = Field(
        default=None,
        description="Optional document ID to search.",
    )

    document_ids: list[uuid.UUID] | None = Field(
        default=None,
        description="Optional list of document IDs to search.",
    )

    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of retrieval results.",
    )

    min_similarity: float | None = Field(
        default=None,
        ge=-1.0,
        le=1.0,
        description="Minimum cosine similarity threshold.",
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Query cannot be empty.")

        return value

    @field_validator("document_ids")
    @classmethod
    def validate_document_ids(
        cls,
        value: list[uuid.UUID] | None,
    ) -> list[uuid.UUID] | None:

        if value is None:
            return None

        if not value:
            raise ValueError("Document IDs cannot be empty.")

        if len(value) != len(set(value)):
            raise ValueError("Duplicate document IDs are not allowed.")

        return value

    @model_validator(mode="after")
    def validate_document_filter(self) -> RetrievalRequest:

        if self.document_id is not None and self.document_ids is not None:
            raise ValueError(
                "Use document_id or document_ids, not both."
            )

        return self


class RetrievedChunkResponse(BaseModel):
    """
    Response schema for an individual retrieved document chunk.
    """

    model_config = ConfigDict(from_attributes=True)

    chunk_id: str
    document_id: uuid.UUID
    chunk_index: int

    text: str

    page_numbers: list[int] = Field(default_factory=list)
    start_page: int | None = None
    end_page: int | None = None

    similarity: float
    distance: float

    provider: str
    model: str
    dimensions: int

    pipeline_version: str
    chunking_version: str


class RetrievalResponse(BaseModel):
    """
    Response schema for semantic retrieval.
    """

    query: str
    results: list[RetrievedChunkResponse]

    total_results: int = Field(ge=0)