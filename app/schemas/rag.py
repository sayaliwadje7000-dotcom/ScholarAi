from pydantic import BaseModel, ConfigDict, Field

from app.schemas.retrieval import RetrievedChunkResponse


class CitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_id: str
    document_id: str
    chunk_id: str
    page_numbers: list[int]
    similarity: float


class CitationIssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    reference: str
    reason: str


class GroundingReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str

    total_paragraphs: int
    cited_paragraphs: int
    uncited_paragraphs: int

    citation_coverage: float = Field(
        ge=0.0,
        le=1.0,
    )

    valid_citations: int
    invalid_citations: int

    issues: list[str]

    requires_review: bool


class RAGAskResponse(BaseModel):
    """
    Structured response returned by the RAG API.
    """

    model_config = ConfigDict(from_attributes=True)

    query: str
    answer: str

    retrieved_chunks: list[RetrievedChunkResponse]

    total_retrieved: int

    grounded: bool

    included_chunks: int
    excluded_chunks: int
    context_characters: int

    citations: list[CitationResponse]

    citation_issues: list[CitationIssueResponse]

    grounding_status: str

    grounding_report: GroundingReportResponse | None