from __future__ import annotations

import re

from dataclasses import dataclass, replace
from typing import Any, Iterable

from app.schemas.external_resources import (
    ExternalResource,
)


RELEVANCE_ALGORITHM_VERSION = "1.0.0"


DEFAULT_FIELD_WEIGHTS = {
    "title_phrase": 30.0,
    "title": 25.0,
    "subject": 15.0,
    "description": 15.0,
    "metadata": 10.0,
    "authors": 5.0,
}


DEFAULT_STOP_WORDS = frozenset({
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "using",
    "what",
    "when",
    "where",
    "which",
    "with",
})


@dataclass(frozen=True, slots=True)
class RelevanceAssessment:
    """
    Explainable relevance assessment for one resource.
    """

    score: float

    matched_terms: tuple[str, ...]

    matched_fields: tuple[str, ...]

    algorithm_version: str = (
        RELEVANCE_ALGORITHM_VERSION
    )

    def __post_init__(self) -> None:

        if not 0.0 <= self.score <= 100.0:
            raise ValueError(
                "Relevance score must be between 0 and 100."
            )

        if not all(
            isinstance(term, str)
            for term in self.matched_terms
        ):
            raise TypeError(
                "Matched terms must contain strings."
            )

        if not all(
            isinstance(field, str)
            for field in self.matched_fields
        ):
            raise TypeError(
                "Matched fields must contain strings."
            )

    def to_dict(self) -> dict[str, Any]:

        return {
            "score": self.score,
            "matched_terms": list(
                self.matched_terms
            ),
            "matched_fields": list(
                self.matched_fields
            ),
            "algorithm_version": (
                self.algorithm_version
            ),
        }


@dataclass(frozen=True, slots=True)
class RelevanceWeights:
    """
    Configurable weights for relevance scoring.
    """

    title_phrase: float = 30.0

    title: float = 25.0

    subject: float = 15.0

    description: float = 15.0

    metadata: float = 10.0

    authors: float = 5.0

    def __post_init__(self) -> None:

        values = (
            self.title_phrase,
            self.title,
            self.subject,
            self.description,
            self.metadata,
            self.authors,
        )

        if any(
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            for value in values
        ):
            raise TypeError(
                "All relevance weights must be numeric."
            )

        if any(value < 0 for value in values):
            raise ValueError(
                "Relevance weights cannot be negative."
            )

        if abs(sum(values) - 100.0) > 0.000001:
            raise ValueError(
                "Relevance weights must total 100."
            )


class ResourceRelevanceRanker:
    """
    Deterministic and explainable educational resource
    relevance scoring and ranking.

    This component evaluates query-to-resource relevance.

    It does not:
    - Evaluate resource credibility.
    - Evaluate resource freshness.
    - Replace Phase 12.7 quality assessment.
    - Use user interaction history.
    - Perform machine learning.
    - Persist resources.
    """

    def __init__(
        self,
        weights: RelevanceWeights | None = None,
        stop_words: Iterable[str] | None = None,
    ) -> None:

        self.weights = (
            weights
            if weights is not None
            else RelevanceWeights()
        )

        self.stop_words = frozenset(
            word.casefold()
            for word in (
                stop_words
                if stop_words is not None
                else DEFAULT_STOP_WORDS
            )
        )

    # -----------------------------------------------------
    # Text normalization
    # -----------------------------------------------------

    @staticmethod
    def _normalize_text(
        value: str | None,
    ) -> str:

        if not value:
            return ""

        value = value.casefold()

        value = re.sub(
            r"[^a-z0-9]+",
            " ",
            value,
        )

        return " ".join(
            value.split()
        )

    def _tokenize(
        self,
        value: str | None,
    ) -> tuple[str, ...]:

        normalized = self._normalize_text(
            value
        )

        if not normalized:
            return ()

        return tuple(
            token
            for token in normalized.split()
            if (
                len(token) > 1
                and token not in self.stop_words
            )
        )

    # -----------------------------------------------------
    # Metadata extraction
    # -----------------------------------------------------

    @staticmethod
    def _metadata_terms(
        metadata: dict[str, Any],
    ) -> str:

        values: list[str] = []

        for key in (
            "topics",
            "keywords",
            "learning_objectives",
            "subject",
            "tags",
        ):

            value = metadata.get(key)

            if isinstance(value, str):

                values.append(value)

            elif isinstance(
                value,
                (list, tuple, set),
            ):

                values.extend(
                    item
                    for item in value
                    if isinstance(item, str)
                )

        return " ".join(values)

    # -----------------------------------------------------
    # Field matching
    # -----------------------------------------------------

    @staticmethod
    def _coverage(
        query_terms: tuple[str, ...],
        field_terms: set[str],
    ) -> float:

        if not query_terms:
            return 0.0

        matched = {
            term
            for term in query_terms
            if term in field_terms
        }

        return (
            len(matched)
            / len(set(query_terms))
        )

    # -----------------------------------------------------
    # Resource scoring
    # -----------------------------------------------------

    def assess(
        self,
        resource: ExternalResource,
        query: str,
    ) -> RelevanceAssessment:

        if not isinstance(
            resource,
            ExternalResource,
        ):
            raise TypeError(
                "Expected an ExternalResource."
            )

        if not isinstance(query, str):
            raise TypeError(
                "Query must be a string."
            )

        normalized_query = (
            self._normalize_text(query)
        )

        query_terms = tuple(
            dict.fromkeys(
                self._tokenize(query)
            )
        )

        if not query_terms:

            return RelevanceAssessment(
                score=0.0,
                matched_terms=(),
                matched_fields=(),
            )

        title = self._normalize_text(
            resource.title
        )

        description = self._normalize_text(
            resource.description
        )

        subject = self._normalize_text(
            resource.subject
        )

        authors = self._normalize_text(
            " ".join(resource.authors)
        )

        metadata = self._normalize_text(
            self._metadata_terms(
                resource.metadata
            )
        )

        title_terms = set(
            self._tokenize(title)
        )

        description_terms = set(
            self._tokenize(description)
        )

        subject_terms = set(
            self._tokenize(subject)
        )

        author_terms = set(
            self._tokenize(authors)
        )

        metadata_terms = set(
            self._tokenize(metadata)
        )

        weights = self.weights

        # Exact normalized query phrase in title.
        title_phrase_score = (
            weights.title_phrase
            if (
                normalized_query
                and normalized_query in title
            )
            else 0.0
        )

        # Query-term coverage by field.
        title_score = (
            weights.title
            * self._coverage(
                query_terms,
                title_terms,
            )
        )

        subject_score = (
            weights.subject
            * self._coverage(
                query_terms,
                subject_terms,
            )
        )

        description_score = (
            weights.description
            * self._coverage(
                query_terms,
                description_terms,
            )
        )

        metadata_score = (
            weights.metadata
            * self._coverage(
                query_terms,
                metadata_terms,
            )
        )

        author_score = (
            weights.authors
            * self._coverage(
                query_terms,
                author_terms,
            )
        )

        total_score = min(
            100.0,
            max(
                0.0,
                title_phrase_score
                + title_score
                + subject_score
                + description_score
                + metadata_score
                + author_score,
            ),
        )

        matched_terms = tuple(
            term
            for term in query_terms
            if (
                term in title_terms
                or term in description_terms
                or term in subject_terms
                or term in metadata_terms
                or term in author_terms
            )
        )

        matched_fields = []

        if title_phrase_score > 0:
            matched_fields.append(
                "title_phrase"
            )

        if title_score > 0:
            matched_fields.append(
                "title"
            )

        if subject_score > 0:
            matched_fields.append(
                "subject"
            )

        if description_score > 0:
            matched_fields.append(
                "description"
            )

        if metadata_score > 0:
            matched_fields.append(
                "metadata"
            )

        if author_score > 0:
            matched_fields.append(
                "authors"
            )

        return RelevanceAssessment(
            score=round(
                total_score,
                4,
            ),
            matched_terms=matched_terms,
            matched_fields=tuple(
                matched_fields
            ),
        )

    # -----------------------------------------------------
    # Assessment attachment
    # -----------------------------------------------------

    def assess_resource(
        self,
        resource: ExternalResource,
        query: str,
    ) -> ExternalResource:

        assessment = self.assess(
            resource,
            query,
        )

        metadata = dict(
            resource.metadata
        )

        metadata["relevance_assessment"] = (
            assessment.to_dict()
        )

        return replace(
            resource,
            metadata=metadata,
        )

    def assess_many(
        self,
        resources: list[ExternalResource],
        query: str,
    ) -> list[ExternalResource]:

        if not isinstance(resources, list):
            raise TypeError(
                "Resources must be provided as a list."
            )

        return [
            self.assess_resource(
                resource,
                query,
            )
            for resource in resources
        ]

    # -----------------------------------------------------
    # Ranking
    # -----------------------------------------------------

    @staticmethod
    def _relevance_score(
        resource: ExternalResource,
    ) -> float:

        assessment = resource.metadata.get(
            "relevance_assessment",
            {},
        )

        if not isinstance(assessment, dict):
            return 0.0

        score = assessment.get(
            "score",
            0.0,
        )

        if (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
        ):
            return 0.0

        return float(score)

    def rank(
        self,
        resources: list[ExternalResource],
        query: str,
    ) -> list[ExternalResource]:

        assessed_resources = self.assess_many(
            resources,
            query,
        )

        # Stable deterministic ordering.
        #
        # Quality scores are deliberately not included
        # in relevance scoring. Quality and relevance
        # remain separate evaluation dimensions.

        return sorted(
            assessed_resources,
            key=lambda resource: (
                -self._relevance_score(resource),
                resource.title.casefold(),
                resource.provider.casefold(),
                resource.external_id.casefold(),
            ),
        )