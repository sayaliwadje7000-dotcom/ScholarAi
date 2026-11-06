from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.rag.context_builder import ContextSource
from app.services.rag.citation_service import CitationResult


@dataclass(frozen=True)
class GroundingReport:
    status: str
    total_paragraphs: int
    cited_paragraphs: int
    uncited_paragraphs: int
    citation_coverage: float
    valid_citations: int
    invalid_citations: int
    issues: list[str]
    requires_review: bool


class GroundingService:
    """
    Performs deterministic citation-integrity and coverage checks.

    This service does not prove semantic entailment or factual accuracy.
    """

    CITATION_PATTERN = re.compile(
        r"\[(S\d+)"
        r"(?:\s*,\s*pp?\.\s*"
        r"(\d+(?:\s*-\s*\d+)?"
        r"(?:\s*,\s*\d+(?:\s*-\s*\d+)?)*)"
        r")?\s*\]",
        re.IGNORECASE,
    )

    def __init__(
        self,
        minimum_coverage: float = 0.80,
        require_citations: bool = True,
    ):
        if not 0 <= minimum_coverage <= 1:
            raise ValueError(
                "minimum_coverage must be between 0 and 1."
            )

        self.minimum_coverage = minimum_coverage
        self.require_citations = require_citations

    @staticmethod
    def _split_paragraphs(answer: str) -> list[str]:
        return [
            paragraph.strip()
            for paragraph in re.split(r"\n\s*\n", answer)
            if paragraph.strip()
        ]

    def verify(
        self,
        answer: str,
        sources: list[ContextSource],
        citation_result: CitationResult,
    ) -> GroundingReport:

        issues: list[str] = []

        if not answer or not answer.strip():
            return GroundingReport(
                status="insufficient_evidence",
                total_paragraphs=0,
                cited_paragraphs=0,
                uncited_paragraphs=0,
                citation_coverage=0.0,
                valid_citations=0,
                invalid_citations=0,
                issues=["The generated answer is empty."],
                requires_review=True,
            )

        paragraphs = self._split_paragraphs(answer)

        source_map = {
            source.source_id.upper(): source
            for source in sources
        }

        cited_paragraphs = 0
        unknown_source_detected = False

        # Check paragraph-level citation coverage.
        for index, paragraph in enumerate(paragraphs, start=1):

            references = self.CITATION_PATTERN.findall(paragraph)

            if references:
                cited_paragraphs += 1

            elif self.require_citations:
                issues.append(
                    f"Paragraph {index} has no source citation."
                )

        total_paragraphs = len(paragraphs)

        coverage = (
            cited_paragraphs / total_paragraphs
            if total_paragraphs
            else 0.0
        )

        # Verify that every cited source exists.
        for source_id, _ in self.CITATION_PATTERN.findall(answer):

            if source_id.upper() not in source_map:
                unknown_source_detected = True

                issues.append(
                    f"Unknown source reference: {source_id}."
                )

        # Include citation validation issues.
        for issue in citation_result.issues:
            issues.append(
                f"Citation validation failed: "
                f"{issue.reference} ({issue.reason})."
            )

        invalid_citations = citation_result.invalid_references

        if unknown_source_detected:
            invalid_citations += 1

        if citation_result.invalid_references:
            issues.append(
                f"{citation_result.invalid_references} invalid "
                "citation reference(s) detected."
            )

        if coverage < self.minimum_coverage:
            issues.append(
                "Citation coverage is below the required threshold."
            )

        # Determine grounding status.
        if invalid_citations > 0:
         status = "invalid_citations"

        elif coverage < self.minimum_coverage:
         status = "insufficient_coverage"

        elif not sources:
         status = "insufficient_evidence"

        else:
         status = "citation_checks_passed"
        return GroundingReport(
            status=status,
            total_paragraphs=total_paragraphs,
            cited_paragraphs=cited_paragraphs,
            uncited_paragraphs=(
                total_paragraphs - cited_paragraphs
            ),
            citation_coverage=round(coverage, 4),
            valid_citations=citation_result.valid_references,
            invalid_citations=invalid_citations,
            issues=issues,
            requires_review=(
                status != "citation_checks_passed"
            ),
        )