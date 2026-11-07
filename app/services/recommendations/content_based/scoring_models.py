from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ContentSimilarityBreakdown:
    embedding_similarity: float | None

    topic_similarity: float | None

    keyword_similarity: float | None

    objective_similarity: float | None

    prerequisite_similarity: float | None

    subject_similarity: float | None

    content_format_similarity: float | None

    difficulty_similarity: float | None

    text_similarity: float | None


@dataclass(frozen=True, slots=True)
class ContentBasedScoreResult:

    reference_resource_id: UUID

    candidate_resource_id: UUID

    score: float

    confidence: float

    breakdown: ContentSimilarityBreakdown

    matched_topics: tuple[str, ...]

    matched_keywords: tuple[str, ...]

    matched_objectives: tuple[str, ...]

    contributing_signals: tuple[str, ...]