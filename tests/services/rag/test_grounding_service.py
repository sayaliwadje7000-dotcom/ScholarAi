import pytest

from app.services.rag.grounding_service import GroundingService
from app.services.rag.context_builder import ContextSource

from app.services.rag.citation_service import (
    CitationResult,
    CitationIssue,
)

@pytest.fixture
def grounding_service():
    return GroundingService()


@pytest.fixture
def source():
    return ContextSource(
        source_id="S1",
        chunk_id="chunk-1",
        document_id="document-1",
        page_numbers=[1, 2, 3],
        similarity=0.85,
    )


@pytest.fixture
def valid_citation_result():
    return CitationResult(
        citations=[],
        issues=[],
        total_references=1,
        valid_references=1,
        invalid_references=0,
    )


def test_valid_citation_coverage(
    grounding_service,
    source,
    valid_citation_result,
):
    answer = (
        "Photosynthesis is the process by which "
        "plants produce food. [S1]\n\n"
        "It requires sunlight. [S1, p. 2]"
    )

    report = grounding_service.verify(
        answer,
        [source],
        valid_citation_result,
    )

    assert report.status == "citation_checks_passed"
    assert report.citation_coverage == 1.0
    assert report.uncited_paragraphs == 0
    assert report.requires_review is False


def test_uncited_paragraph_detected(
    grounding_service,
    source,
    valid_citation_result,
):
    answer = (
        "Photosynthesis produces food. [S1]\n\n"
        "Plants also need water."
    )

    report = grounding_service.verify(
        answer,
        [source],
        valid_citation_result,
    )

    assert report.cited_paragraphs == 1
    assert report.uncited_paragraphs == 1
    assert report.citation_coverage == 0.5
    assert report.status == "insufficient_coverage"
    assert report.requires_review is True


def test_unknown_source_detected(
    grounding_service,
    source,
    valid_citation_result,
):
    answer = "This statement uses an unknown source. [S2]"

    report = grounding_service.verify(
        answer,
        [source],
        valid_citation_result,
    )

    assert report.status == "invalid_citations"
    assert any(
        "Unknown source reference" in issue
        for issue in report.issues
    )


def test_invalid_citations_detected(
    grounding_service,
    source,
):
    citation_result = CitationResult(
        citations=[],
        issues=[
            CitationIssue(
                reference="[S1, p. 10]",
                reason="Page does not exist.",
            )
        ],
        total_references=1,
        valid_references=0,
        invalid_references=1,
    )

    report = grounding_service.verify(
        "This is a statement. [S1, p. 10]",
        [source],
        citation_result,
    )

    assert report.status == "invalid_citations"
    assert report.invalid_citations == 1
    assert report.requires_review is True


def test_empty_answer(
    grounding_service,
    source,
    valid_citation_result,
):
    report = grounding_service.verify(
        "",
        [source],
        valid_citation_result,
    )

    assert report.status == "insufficient_evidence"
    assert report.requires_review is True


def test_empty_sources(
    grounding_service,
    valid_citation_result,
):
    report = grounding_service.verify(
        "An answer without citations.",
        [],
        valid_citation_result,
    )

    assert report.status == "insufficient_coverage"
    assert report.requires_review is True


def test_custom_coverage_threshold(
    source,
    valid_citation_result,
):
    service = GroundingService(
        minimum_coverage=1.0
    )

    answer = (
        "First statement. [S1]\n\n"
        "Second statement."
    )

    report = service.verify(
        answer,
        [source],
        valid_citation_result,
    )

    assert report.citation_coverage == 0.5
    assert report.status == "insufficient_coverage"


def test_invalid_threshold():
    with pytest.raises(ValueError):
        GroundingService(minimum_coverage=1.5)


def test_citation_requirement_can_be_disabled(
    source,
    valid_citation_result,
):
    service = GroundingService(
        minimum_coverage=0.0,
        require_citations=False,
    )

    report = service.verify(
        "An uncited paragraph.",
        [source],
        valid_citation_result,
    )

    assert report.uncited_paragraphs == 1
    assert report.status == "citation_checks_passed"
