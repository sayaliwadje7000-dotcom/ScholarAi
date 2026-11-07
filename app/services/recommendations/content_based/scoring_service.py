import math

from dataclasses import dataclass
from uuid import UUID

from app.services.recommendations.content_based.feature_extractor import (
    ExtractedContentFeatures,
)

from app.services.recommendations.content_based.scoring_models import (
    ContentBasedScoreResult,
    ContentSimilarityBreakdown,
)


class ContentBasedScoringError(ValueError):
    """Raised when content-based scoring inputs are invalid."""


@dataclass(frozen=True, slots=True)
class ContentScoringWeights:

    embedding: float = 0.35

    topics: float = 0.20

    keywords: float = 0.15

    objectives: float = 0.15

    prerequisites: float = 0.05

    subject: float = 0.05

    content_format: float = 0.03

    difficulty: float = 0.02

    text: float = 0.05

    def __post_init__(self):

        values = (
            self.embedding,
            self.topics,
            self.keywords,
            self.objectives,
            self.prerequisites,
            self.subject,
            self.content_format,
            self.difficulty,
            self.text,
        )

        for value in values:

            if isinstance(value, bool):

                raise ContentBasedScoringError(
                    "Scoring weights must be numeric."
                )

            if not isinstance(value, (int, float)):

                raise ContentBasedScoringError(
                    "Scoring weights must be numeric."
                )

            if not math.isfinite(value) or value < 0:

                raise ContentBasedScoringError(
                    "Scoring weights must be finite and non-negative."
                )

        if sum(values) <= 0:

            raise ContentBasedScoringError(
                "At least one scoring weight must be positive."
            )


class ContentBasedScoringService:
    """
    Computes content-based similarity between two resources.

    The service combines semantic embedding similarity with
    normalized resource-content feature similarity.

    It does not access the database or modify resource records.
    """

    def __init__(
        self,
        weights: ContentScoringWeights | None = None,
    ):

        self.weights = weights or ContentScoringWeights()

    @staticmethod
    def _validate_features(features):

        if not isinstance(
            features,
            ExtractedContentFeatures,
        ):

            raise ContentBasedScoringError(
                "Expected ExtractedContentFeatures."
            )

        if not isinstance(features.resource_id, UUID):

            raise ContentBasedScoringError(
                "Resource ID must be a UUID."
            )

    @staticmethod
    def _normalize_terms(values):

        if values is None:
            return frozenset()

        if isinstance(values, str):

            values = (values,)

        try:

            return frozenset(
                value.strip().casefold()
                for value in values
                if isinstance(value, str) and value.strip()
            )

        except TypeError:

            raise ContentBasedScoringError(
                "Feature values must be iterable."
            ) from None

    @staticmethod
    def _jaccard_similarity(left, right):

        left = frozenset(left)

        right = frozenset(right)

        if not left or not right:

            return None

        union = left | right

        if not union:

            return None

        return len(left & right) / len(union)

    @staticmethod
    def _categorical_similarity(left, right):

        if not left or not right:

            return None

        left = left.strip().casefold()

        right = right.strip().casefold()

        if not left or not right:

            return None

        return 1.0 if left == right else 0.0

    @staticmethod
    def _difficulty_similarity(left, right):

        if not left or not right:

            return None

        levels = {
            "beginner": 0,
            "intermediate": 1,
            "advanced": 2,
        }

        left = left.strip().casefold()

        right = right.strip().casefold()

        if left not in levels or right not in levels:

            return None

        difference = abs(
            levels[left] - levels[right]
        )

        return max(0.0, 1.0 - (difference * 0.5))

    @staticmethod
    def _validate_embedding_similarity(value):

        if value is None:

            return None

        if isinstance(value, bool):

            raise ContentBasedScoringError(
                "Embedding similarity must be numeric."
            )

        if not isinstance(value, (int, float)):

            raise ContentBasedScoringError(
                "Embedding similarity must be numeric."
            )

        if not math.isfinite(value):

            raise ContentBasedScoringError(
                "Embedding similarity must be finite."
            )

        if value < -1.0 or value > 1.0:

            raise ContentBasedScoringError(
                "Embedding similarity must be between -1 and 1."
            )

        # Convert cosine similarity [-1, 1]
        # into normalized similarity [0, 1].

        return (value + 1.0) / 2.0

    def _calculate_components(
        self,
        reference,
        candidate,
        embedding_similarity,
    ):

        return {

            "embedding": embedding_similarity,

            "topics": self._jaccard_similarity(
                self._normalize_terms(reference.topics),
                self._normalize_terms(candidate.topics),
            ),

            "keywords": self._jaccard_similarity(
                self._normalize_terms(reference.keywords),
                self._normalize_terms(candidate.keywords),
            ),

            "objectives": self._jaccard_similarity(
                self._normalize_terms(reference.learning_objectives),
                self._normalize_terms(candidate.learning_objectives),
            ),

            "prerequisites": self._jaccard_similarity(
                self._normalize_terms(reference.prerequisites),
                self._normalize_terms(candidate.prerequisites),
            ),

            "subject": self._categorical_similarity(
                reference.subject,
                candidate.subject,
            ),

            "content_format": self._categorical_similarity(
                reference.content_format,
                candidate.content_format,
            ),

            "difficulty": self._difficulty_similarity(
                reference.difficulty,
                candidate.difficulty,
            ),

            "text": self._jaccard_similarity(
                self._normalize_terms(reference.tokens),
                self._normalize_terms(candidate.tokens),
            ),
        }

    def score(
        self,
        reference: ExtractedContentFeatures,
        candidate: ExtractedContentFeatures,
        embedding_similarity: float | None = None,
    ) -> ContentBasedScoreResult:

        self._validate_features(reference)

        self._validate_features(candidate)

        normalized_embedding = (
            self._validate_embedding_similarity(
                embedding_similarity
            )
        )

        weights = {

            "embedding": self.weights.embedding,

            "topics": self.weights.topics,

            "keywords": self.weights.keywords,

            "objectives": self.weights.objectives,

            "prerequisites": self.weights.prerequisites,

            "subject": self.weights.subject,

            "content_format": self.weights.content_format,

            "difficulty": self.weights.difficulty,

            "text": self.weights.text,
        }

        components = self._calculate_components(
            reference,
            candidate,
            normalized_embedding,
        )

        available_signals = {

            name: value

            for name, value in components.items()

            if value is not None and weights[name] > 0
        }

        total_available_weight = sum(
            weights[name]
            for name in available_signals
        )

        if total_available_weight == 0:

            final_score = 0.0

            confidence = 0.0

        else:

            weighted_score = sum(
                value * weights[name]
                for name, value in available_signals.items()
            )

            final_score = (
                weighted_score / total_available_weight
            )

            total_configured_weight = sum(
                weights.values()
            )

            confidence = (
                total_available_weight
                / total_configured_weight
            )

        matched_topics = tuple(
            sorted(
                self._normalize_terms(reference.topics)
                & self._normalize_terms(candidate.topics)
            )
        )

        matched_keywords = tuple(
            sorted(
                self._normalize_terms(reference.keywords)
                & self._normalize_terms(candidate.keywords)
            )
        )

        matched_objectives = tuple(
            sorted(
                self._normalize_terms(reference.learning_objectives)
                & self._normalize_terms(candidate.learning_objectives)
            )
        )

        breakdown = ContentSimilarityBreakdown(

            embedding_similarity=components["embedding"],

            topic_similarity=components["topics"],

            keyword_similarity=components["keywords"],

            objective_similarity=components["objectives"],

            prerequisite_similarity=components["prerequisites"],

            subject_similarity=components["subject"],

            content_format_similarity=components["content_format"],

            difficulty_similarity=components["difficulty"],

            text_similarity=components["text"],
        )

        return ContentBasedScoreResult(

            reference_resource_id=reference.resource_id,

            candidate_resource_id=candidate.resource_id,

            score=round(final_score, 6),

            confidence=round(confidence, 6),

            breakdown=breakdown,

            matched_topics=matched_topics,

            matched_keywords=matched_keywords,

            matched_objectives=matched_objectives,

            contributing_signals=tuple(
                available_signals.keys()
            ),
        )