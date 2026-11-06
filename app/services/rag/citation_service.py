
from __future__ import annotations

import re

from dataclasses import dataclass

from app.services.rag.context_builder import ContextSource


@dataclass(frozen=True)
class Citation:
    source_id: str
    document_id: str
    chunk_id: str
    page_numbers: list[int]
    similarity: float


@dataclass(frozen=True)
class CitationIssue:
    reference: str
    reason: str


@dataclass(frozen=True)
class CitationResult:
    citations: list[Citation]
    issues: list[CitationIssue]
    total_references: int
    valid_references: int
    invalid_references: int


class CitationService:

    CITATION_PATTERN = re.compile(
        r"\[(S\d+)"
        r"(?:\s*,\s*pp?\.\s*"
        r"(\d+(?:\s*-\s*\d+)?"
        r"(?:\s*,\s*\d+(?:\s*-\s*\d+)?)*)"
        r")?\s*\]",
        re.IGNORECASE,
    )

    @staticmethod
    def _parse_pages(expression: str | None) -> list[int] | None:

        if expression is None:
            return []

        pages = set()

        try:
            for part in expression.split(","):

                part = part.strip()

                if "-" in part:
                    start, end = map(
                        int,
                        part.split("-", maxsplit=1),
                    )

                    if start < 1 or end < start:
                        return None

                    if end - start > 100:
                        return None

                    pages.update(range(start, end + 1))

                else:
                    page = int(part)

                    if page < 1:
                        return None

                    pages.add(page)

        except (ValueError, TypeError):
            return None

        return sorted(pages)

    def extract(
        self,
        answer: str,
        sources: list[ContextSource],
    ) -> CitationResult:

        source_map = {
            source.source_id.upper(): source
            for source in sources
        }

        citations = []
        issues = []
        seen = set()

        matches = list(self.CITATION_PATTERN.finditer(answer))

        valid_count = 0

        for match in matches:

            reference = match.group(0)
            source_id = match.group(1).upper()
            page_expression = match.group(2)

            source = source_map.get(source_id)

            # Validate source identifier
            if source is None:
                issues.append(
                    CitationIssue(
                        reference=reference,
                        reason="Unknown source identifier.",
                    )
                )
                continue

            # Validate page expression
            requested_pages = self._parse_pages(
                page_expression
            )

            if requested_pages is None:
                issues.append(
                    CitationIssue(
                        reference=reference,
                        reason="Invalid page range.",
                    )
                )
                continue

            available_pages = set(
                source.page_numbers or []
            )

            if requested_pages:

                invalid_pages = (
                    set(requested_pages) - available_pages
                )

                if invalid_pages:
                    issues.append(
                        CitationIssue(
                            reference=reference,
                            reason=(
                                "Cited page number is not available "
                                "in retrieved source metadata."
                            ),
                        )
                    )
                    continue

                cited_pages = requested_pages

            else:
                cited_pages = sorted(available_pages)

            # IMPORTANT:
            # Count every valid occurrence BEFORE deduplication.
            valid_count += 1

            # Deduplicate structured citations only.
            citation_key = (
                source_id,
                tuple(cited_pages),
            )

            if citation_key in seen:
                continue

            seen.add(citation_key)

            citations.append(
                Citation(
                    source_id=source.source_id,
                    document_id=source.document_id,
                    chunk_id=source.chunk_id,
                    page_numbers=cited_pages,
                    similarity=source.similarity,
                )
            )

        return CitationResult(
            citations=citations,
            issues=issues,
            total_references=len(matches),
            valid_references=valid_count,
            invalid_references=len(issues),
        )
