from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.models.study_resource import StudyResource


@dataclass(frozen=True, slots=True)
class ResourceSimilarityResult:
    """
    Represents the similarity between a query vector
    and an educational resource.
    """

    resource_id: UUID

    resource: StudyResource

    embedding_id: UUID

    cosine_distance: float

    similarity_score: float


@dataclass(frozen=True, slots=True)
class ResourceComparisonResult:
    """
    Represents similarity between two educational resources.
    """

    source_resource_id: UUID

    target_resource_id: UUID

    cosine_distance: float

    similarity_score: float