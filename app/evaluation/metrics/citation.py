from collections.abc import Sequence
from typing import TypeVar

T = TypeVar("T")


def _validate_citations(
    citations: Sequence[T],
    reference_citations: Sequence[T],
) -> None:
    if isinstance(citations, (str, bytes)):
        raise TypeError("citations must be a sequence, not a string")

    if isinstance(reference_citations, (str, bytes)):
        raise TypeError("reference_citations must be a sequence, not a string")


def _overlap_ratio(
    citations: Sequence[T],
    reference_citations: Sequence[T],
) -> float:
    _validate_citations(citations, reference_citations)

    if not citations:
        return 0.0

    matched = set(citations).intersection(set(reference_citations))
    return len(matched) / len(citations)


def citation_precision(
    citations: Sequence[T],
    reference_citations: Sequence[T],
) -> float:
    """Calculate the proportion of supplied citations matching references."""
    return _overlap_ratio(citations, reference_citations)


def citation_recall(
    citations: Sequence[T],
    reference_citations: Sequence[T],
) -> float:
    """Calculate citation overlap relative to the supplied citation list."""
    return _overlap_ratio(citations, reference_citations)


def citation_coverage(
    citations: Sequence[T],
    reference_citations: Sequence[T],
) -> float:
    """Calculate the proportion of supplied citations covered by references."""
    return _overlap_ratio(citations, reference_citations)