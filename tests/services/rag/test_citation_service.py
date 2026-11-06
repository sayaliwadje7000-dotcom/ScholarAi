
import pytest

from app.services.rag.context_builder import ContextSource
from app.services.rag.citation_service import CitationService


@pytest.fixture
def sources():
    return [
        ContextSource(
            source_id="S1",
            chunk_id="chunk-001",
            document_id="document-001",
            page_numbers=[5, 6, 7],
            similarity=0.95,
        ),
        ContextSource(
            source_id="S2",
            chunk_id="chunk-002",
            document_id="document-002",
            page_numbers=[10, 11],
            similarity=0.89,
        ),
    ]


@pytest.fixture
def service():
    return CitationService()


def test_extracts_valid_source_citation(service, sources):
    result = service.extract("Binary search [S1].", sources)

    assert result.total_references == 1
    assert result.valid_references == 1
    assert result.invalid_references == 0
    assert result.citations[0].source_id == "S1"


def test_extracts_page_citation(service, sources):
    result = service.extract("Binary search [S1, p. 5].", sources)

    assert result.citations[0].page_numbers == [5]


def test_extracts_page_range(service, sources):
    result = service.extract("Binary search [S1, pp. 5-7].", sources)

    assert result.citations[0].page_numbers == [5, 6, 7]


def test_extracts_multiple_pages(service, sources):
    result = service.extract("Binary search [S1, p. 5, 7].", sources)

    assert result.citations[0].page_numbers == [5, 7]


def test_extracts_multiple_sources(service, sources):
    result = service.extract(
        "First claim [S1]. Second claim [S2].",
        sources,
    )

    assert result.valid_references == 2
    assert result.invalid_references == 0
    assert {c.source_id for c in result.citations} == {"S1", "S2"}


def test_rejects_unknown_source(service, sources):
    result = service.extract("Unsupported reference [S9].", sources)

    assert result.total_references == 1
    assert result.invalid_references == 1
    assert result.valid_references == 0


def test_rejects_unavailable_page(service, sources):
    result = service.extract("Reference [S1, p. 99].", sources)

    assert result.invalid_references == 1
    assert result.valid_references == 0


def test_removes_duplicate_citations(service, sources):
    result = service.extract(
        "Claim [S1]. Another claim [S1].",
        sources,
    )

    assert result.total_references == 2
    assert result.valid_references == 2
    assert result.invalid_references == 0
    assert len(result.citations) == 1


def test_rejects_invalid_page_range(service, sources):
    result = service.extract(
        "Invalid reference [S1, pp. 7-5].",
        sources,
    )

    assert result.invalid_references == 1
    assert result.valid_references == 0


def test_handles_answer_without_citations(service, sources):
    result = service.extract(
        "Binary search is an algorithm.",
        sources,
    )

    assert result.total_references == 0
    assert result.valid_references == 0
    assert result.invalid_references == 0
    assert result.citations == []


def test_preserves_document_and_chunk_attribution(service, sources):
    result = service.extract("Evidence [S1].", sources)

    citation = result.citations[0]

    assert citation.document_id == "document-001"
    assert citation.chunk_id == "chunk-001"
    assert citation.similarity == 0.95


def test_handles_empty_source_list(service):
    result = service.extract("Reference [S1].", [])

    assert result.total_references == 1
    assert result.invalid_references == 1
    assert result.valid_references == 0


def test_case_insensitive_source_identifiers(service, sources):
    result = service.extract("Reference [s1].", sources)

    assert result.valid_references == 1
    assert result.citations[0].source_id == "S1"


def test_multiple_duplicate_citations_preserve_occurrence_count(
    service, sources
):
    result = service.extract(
        "[S1] [S1] [S1, p. 5] [S1, p. 5]",
        sources,
    )

    assert result.total_references == 4
    assert result.valid_references == 4
    assert result.invalid_references == 0
    assert len(result.citations) == 2


def test_mixed_valid_and_invalid_citations(service, sources):
    result = service.extract(
        "[S1] [S9] [S2, p. 99]",
        sources,
    )

    assert result.total_references == 3
    assert result.valid_references == 1
    assert result.invalid_references == 2
    assert len(result.citations) == 1
