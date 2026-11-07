from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user_resource_interaction import UserResourceInteraction

from app.schemas.content_recommendations import (
    ContentRecommendationRequest,
    ContentRecommendationResponse,
    ContentRecommendationItem,
)

from app.services.recommendations.content_based.query_context import (
    ContentQueryFilters,
)


class ContentRecommendationServiceError(Exception):
    """Base recommendation service error."""


class ContentBasedRecommendationService:

    ALGORITHM_VERSION = "content-based-v1"

    def __init__(
        self,
        query_context_service,
        similarity_service,
        feature_extractor,
        scoring_service,
        filtering_service,
        ranking_service,
    ):
        self.query_context_service = query_context_service
        self.similarity_service = similarity_service
        self.feature_extractor = feature_extractor
        self.scoring_service = scoring_service
        self.filtering_service = filtering_service
        self.ranking_service = ranking_service

    def _load_interactions(
        self,
        db: Session,
        user_id: UUID,
    ):
        """
        Load recent user interactions.

        A missing database session returns an empty interaction
        collection for isolated unit tests. Production API calls
        should always provide a valid database session.
        """

        if db is None:
            return []

        statement = (
            select(UserResourceInteraction)
            .where(
                UserResourceInteraction.user_id == user_id
            )
            .order_by(
                UserResourceInteraction.occurred_at.desc()
            )
            .limit(20)
        )

        return list(db.scalars(statement).all())

    def _build_context(
        self,
        db: Session,
        user_id: UUID,
        request: ContentRecommendationRequest,
    ):
        filters = ContentQueryFilters(
            subject=request.subject,
            language=request.language,
            difficulty_level=request.difficulty_level,
            resource_types=tuple(request.resource_types),
            exclude_completed=request.exclude_completed,
        )

        return self.query_context_service.build(
            db=db,
            user_id=user_id,
            query_text=request.query,
            filters=filters,
        )

    def _retrieve_candidates(
        self,
        db: Session,
        context,
        request: ContentRecommendationRequest,
    ):
        return self.similarity_service.find_similar_resources(
            db=db,
            query_vector=context.query_embedding,
            limit=min(request.limit * 5, 100),
            min_similarity=request.minimum_similarity,
            subject=request.subject,
            language=request.language,
        )

    def _score_candidates(
        self,
        similarity_results,
        context,
    ):
        candidates = []

        for result in similarity_results:
            resource = result.resource

            features = self.feature_extractor.extract(
                resource
            )

            if not self._has_usable_features(features):
                continue

            scoring_result = self.scoring_service.score(
                reference_features=context,
                candidate_features=features,
            )

            if scoring_result is None:
                continue

            candidates.append(
                (features, scoring_result)
            )

        return candidates

    @staticmethod
    def _has_usable_features(features):
        return bool(
            features.tokens
            or features.topics
            or features.keywords
            or features.learning_objectives
        )

    def _filter_candidates(
        self,
        candidates,
        request: ContentRecommendationRequest,
        interactions,
    ):
        from app.services.recommendations.content_based.candidate_models import (
            ContentBasedCandidate,
        )

        from app.services.recommendations.content_based.filtering_service import (
            ContentFilterCriteria,
        )

        wrapped_candidates = []

        for features, scoring_result in candidates:
            wrapped_candidates.append(
                ContentBasedCandidate(
                    features=features,
                    scoring_result=scoring_result,
                    is_active=True,
                    quality_score=None,
                )
            )

        criteria = ContentFilterCriteria(
            resource_types=tuple(request.resource_types),
            subjects=(
                (request.subject,)
                if request.subject
                else ()
            ),
            languages=(
                (request.language,)
                if request.language
                else ()
            ),
            difficulty_levels=(
                (request.difficulty_level,)
                if request.difficulty_level
                else ()
            ),
            minimum_score=0.0,
            excluded_resource_ids=(),
            exclude_inactive=True,
        )

        return self.filtering_service.filter(
            candidates=wrapped_candidates,
            criteria=criteria,
        )

    def _rank_candidates(
        self,
        candidates,
        limit: int,
    ):
        return self.ranking_service.rank(
            candidates=candidates,
            limit=limit,
        )

    @staticmethod
    def _build_recommendation_item(
        ranked,
        similarity_results,
    ):
        candidate = ranked.candidate

        features = candidate.features
        score = candidate.scoring_result

        similarity_by_id = {
            result.resource_id: result
            for result in similarity_results
        }

        similarity_result = similarity_by_id.get(
            features.resource_id
        )

        similarity_score = (
            similarity_result.similarity_score
            if similarity_result is not None
            else 0.0
        )

        resource = (
            similarity_result.resource
            if similarity_result is not None
            else None
        )

        return ContentRecommendationItem(
            resource_id=features.resource_id,
            title=features.title,
            description=getattr(
                resource,
                "description",
                None,
            ),
            resource_type=features.resource_type,
            subject=features.subject,
            language=features.language,
            difficulty_level=features.difficulty,
            url=getattr(
                resource,
                "url",
                None,
            ),
            similarity_score=similarity_score,
            content_score=score.score,
            confidence=score.confidence,
            matched_topics=list(score.matched_topics),
            matched_keywords=list(score.matched_keywords),
            matched_objectives=list(score.matched_objectives),
            explanation=(
                "Recommended based on the relevance of "
                "the resource's content to your learning query."
            ),
        )

    def recommend(
        self,
        db: Session,
        user_id: UUID,
        request: ContentRecommendationRequest,
    ) -> ContentRecommendationResponse:

        if not isinstance(user_id, UUID):
            raise ValueError("Invalid user ID.")

        if not isinstance(
            request,
            ContentRecommendationRequest,
        ):
            raise TypeError(
                "Expected ContentRecommendationRequest."
            )

        try:
            interactions = self._load_interactions(
                db=db,
                user_id=user_id,
            )

            context = self._build_context(
                db=db,
                user_id=user_id,
                request=request,
            )

            similarity_results = self._retrieve_candidates(
                db=db,
                context=context,
                request=request,
            )

            scored_candidates = self._score_candidates(
                similarity_results=similarity_results,
                context=context,
            )

            filtered_candidates = self._filter_candidates(
                candidates=scored_candidates,
                request=request,
                interactions=interactions,
            )

            ranked_candidates = self._rank_candidates(
                candidates=filtered_candidates,
                limit=request.limit,
            )

            recommendations = [
                self._build_recommendation_item(
                    ranked=ranked,
                    similarity_results=similarity_results,
                )
                for ranked in ranked_candidates
            ]

            return ContentRecommendationResponse(
                query=request.query,
                total_results=len(recommendations),
                recommendations=recommendations,
                algorithm_version=self.ALGORITHM_VERSION,
            )

        except Exception as exc:
            raise ContentRecommendationServiceError(
                "Content recommendation generation failed."
            ) from exc