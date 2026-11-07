"""
Phase 11.3: Resource Content Representation.

Converts normalized resource features into a deterministic,
structured representation suitable for embedding generation,
semantic similarity computation, and recommendation ranking.

This module:
- Does not access the database.
- Does not call external APIs.
- Does not generate embeddings.
- Does not modify resource records.
"""

from __future__ import annotations

import hashlib
import json

from dataclasses import dataclass
from typing import Iterable

from app.services.recommendations.content_based.feature_extractor import (
    ExtractedContentFeatures,
)
from app.services.recommendations.content_based.feature_normalizer import (
    ContentFeatureNormalizer,
)


@dataclass(frozen=True, slots=True)
class ContentSection:
    """
    Represents one semantic section of a resource.

    Weight is metadata for downstream recommendation
    and embedding-related processing. It does not cause
    the section text to be duplicated.
    """

    name: str
    text: str
    weight: float
    tokens: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Section name cannot be empty.")

        if not self.text or not self.text.strip():
            raise ValueError("Section text cannot be empty.")

        if self.weight <= 0:
            raise ValueError("Section weight must be positive.")

        if not isinstance(self.tokens, tuple):
            raise TypeError("Section tokens must be a tuple.")


@dataclass(frozen=True, slots=True)
class ResourceContentRepresentation:
    """
    Immutable representation of an educational resource.

    The representation separates:
    - Original semantic sections.
    - Embedding-ready serialized text.
    - Normalized tokens.
    - Resource metadata.
    - Content fingerprint.
    """

    resource_id: str
    title: str
    resource_type: str

    sections: tuple[ContentSection, ...]

    embedding_text: str
    tokens: tuple[str, ...]

    language: str
    difficulty: str

    feature_count: int
    content_hash: str

    @property
    def has_semantic_content(self) -> bool:
        return bool(self.embedding_text.strip())

    @property
    def section_count(self) -> int:
        return len(self.sections)

    @property
    def token_count(self) -> int:
        return len(self.tokens)

    def get_section(self, name: str) -> ContentSection | None:
        """
        Retrieve a section by its name.
        """

        normalized_name = name.casefold().strip()

        for section in self.sections:
            if section.name.casefold() == normalized_name:
                return section

        return None


class ResourceRepresentationBuilder:
    """
    Builds deterministic resource content representations.

    Input:
        ExtractedContentFeatures

    Output:
        ResourceContentRepresentation
    """

    SECTION_WEIGHTS = {
        "title": 3.0,
        "description": 1.0,
        "subject": 2.0,
        "resource_type": 1.5,
        "categories": 1.5,
        "topics": 2.5,
        "keywords": 2.0,
        "learning_objectives": 3.0,
        "prerequisites": 1.5,
        "content_format": 1.0,
    }

    def __init__(
        self,
        normalizer: ContentFeatureNormalizer | None = None,
    ) -> None:
        self.normalizer = (
            normalizer or ContentFeatureNormalizer()
        )

    def _build_section(
        self,
        name: str,
        value: str | Iterable[str],
    ) -> ContentSection | None:
        """
        Build a section only when it contains meaningful text.
        """

        if isinstance(value, str):
            normalized_text = self.normalizer.normalize_text(value)

        else:
            normalized_values = self.normalizer.normalize_terms(value)

            normalized_text = "; ".join(normalized_values)

        if not normalized_text:
            return None

        section_tokens = self.normalizer.tokenize(
            [normalized_text]
        )

        if not section_tokens:
            return None

        return ContentSection(
            name=name,
            text=normalized_text,
            weight=self.SECTION_WEIGHTS[name],
            tokens=section_tokens,
        )

    def _build_sections(
        self,
        features: ExtractedContentFeatures,
    ) -> tuple[ContentSection, ...]:
        """
        Convert extracted feature groups into semantic sections.
        """

        section_definitions = [
            ("title", features.title),
            ("description", features.description),
            ("subject", features.subject),
            ("resource_type", features.resource_type),
            ("categories", features.category_slugs),
            ("topics", features.topics),
            ("keywords", features.keywords),
            ("learning_objectives", features.learning_objectives),
            ("prerequisites", features.prerequisites),
            ("content_format", features.content_format),
        ]

        sections: list[ContentSection] = []

        for name, value in section_definitions:
            section = self._build_section(name, value)

            if section is not None:
                sections.append(section)

        return tuple(sections)

    @staticmethod
    def _serialize_sections(
        sections: tuple[ContentSection, ...],
    ) -> str:
        """
        Produce deterministic embedding-ready text.

        Section order is fixed by the builder.
        Labels preserve semantic context.
        """

        serialized_parts = []

        for section in sections:
            serialized_parts.append(
                f"{section.name.replace('_', ' ').title()}: "
                f"{section.text}"
            )

        return "\n".join(serialized_parts)

    @staticmethod
    def _generate_content_hash(
        resource_id: str,
        resource_type: str,
        sections: tuple[ContentSection, ...],
    ) -> str:
        """
        Generate a stable SHA-256 fingerprint.

        The fingerprint changes when semantic content changes.
        It does not depend on runtime object identity.
        """

        payload = {
            "resource_id": resource_id,
            "resource_type": resource_type,
            "sections": [
                {
                    "name": section.name,
                    "text": section.text,
                    "weight": section.weight,
                }
                for section in sections
            ],
        }

        canonical_payload = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

        return hashlib.sha256(
            canonical_payload.encode("utf-8")
        ).hexdigest()

    def build(
        self,
        features: ExtractedContentFeatures,
    ) -> ResourceContentRepresentation:
        """
        Build a complete resource representation.
        """

        if not isinstance(features, ExtractedContentFeatures):
            raise TypeError(
                "features must be an ExtractedContentFeatures instance."
            )

        sections = self._build_sections(features)

        if not sections:
            raise ValueError(
                "Resource must contain at least one meaningful content section."
            )

        embedding_text = self._serialize_sections(sections)

        tokens = self.normalizer.tokenize(
            [section.text for section in sections]
        )

        if not tokens:
            raise ValueError(
                "Resource representation must contain meaningful tokens."
            )

        content_hash = self._generate_content_hash(
            resource_id=features.resource_id,
            resource_type=features.resource_type,
            sections=sections,
        )

        return ResourceContentRepresentation(
            resource_id=features.resource_id,
            title=features.title,
            resource_type=features.resource_type,
            sections=sections,
            embedding_text=embedding_text,
            tokens=tokens,
            language=features.language,
            difficulty=features.difficulty,
            feature_count=features.feature_count,
            content_hash=content_hash,
        )