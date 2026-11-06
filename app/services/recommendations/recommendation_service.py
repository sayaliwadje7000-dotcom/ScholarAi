from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.study_resource import StudyResource
from app.models.user import User
from app.models.user_resource_interaction import (
    UserResourceInteraction,
)
from app.models.recommendation import Recommendation

from app.schemas.recommendations import (
    RecommendationRequest,
)

from app.services.recommendations.resource_classifier import (
    ResourceClassifier,
)

from app.services.recommendations.context_builder import (
    LearningContextBuilder,
)

from app.services.recommendations.scoring_service import (
    RecommendationScoringService,
)

from app.services.recommendations.filtering_service import (
    RecommendationFilteringService,
)

from app.services.recommendations.ranking_service import (
    RecommendationRankingService,
)

from app.services.recommendations.explanation_service import (
    RecommendationExplanationService,
)


class RecommendationServiceError(Exception):
    pass


class RecommendationApplicationService:
    """
    Application-level orchestration for ScholarAI recommendations.

    Coordinates classification, context construction, scoring,
    filtering, ranking, explanations and persistence.
    """

    def __init__(
        self,
        classifier=None,
        context_builder=None,
        scoring_service=None,
        filtering_service=None,
        ranking_service=None,
        explanation_service=None,
    ):
        self.classifier = (
            classifier or ResourceClassifier()
        )

        self.context_builder = (
            context_builder or LearningContextBuilder()
        )

        self.scoring_service = (
            scoring_service or RecommendationScoringService()
        )

        self.filtering_service = (
            filtering_service or RecommendationFilteringService()
        )

        self.ranking_service = (
            ranking_service or RecommendationRankingService()
        )

        self.explanation_service = (
            explanation_service
            or RecommendationExplanationService()
        )

    def _load_interactions(
        self,
        db: Session,
        user_id: UUID,
    ):
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

    def _load_resources(
        self,
        db: Session,
    ):
        statement = (
            select(StudyResource)
            .where(
                StudyResource.is_active.is_(True)
            )
            .options(
                selectinload(StudyResource.categories)
            )
            .order_by(
                StudyResource.created_at.desc()
            )
        )

        return list(db.scalars(statement).all())

    def generate(
        self,
        db: Session,
        user: User,
        request: RecommendationRequest,
    ):
        """
        Generate and persist personalized recommendations.

        All persistence occurs inside one transaction.
        """

        if not isinstance(user, User):
            raise TypeError("Expected authenticated User.")

        if not isinstance(request, RecommendationRequest):
            raise TypeError("Expected RecommendationRequest.")

        try:
            interactions = self._load_interactions(
                db,
                user.id,
            )

            resources = self._load_resources(db)

            context = self.context_builder.build(
                user=user,
                preferences=user.preferences,
                request=request,
                interactions=interactions,
            )

            classified_resources = [
                self.classifier.classify(resource)
                for resource in resources
            ]

            scored_candidates = []

            for resource, classification in zip(
                resources,
                classified_resources,
            ):
                scoring_result = self.scoring_service.score(
                    classification,
                    context,
                )

                if scoring_result is None:
                    continue

                scored_candidates.append(
                    (
                        classification,
                        scoring_result,
                    )
                )

            filtered_candidates = self.filtering_service.filter(
                candidates=scored_candidates,
                request=request,
                interactions=interactions,
            )

            ranked = self.ranking_service.rank(
                candidates=filtered_candidates,
                limit=request.limit,
            )

            explanations = self.explanation_service.explain_many(
                ranked_recommendations=ranked,
                context=context,
            )

            recommendation_records = []

            for ranked_item, explanation in zip(
                ranked,
                explanations,
            ):
                resource = ranked_item.resource

                database_resource = next(
                    (
                        item
                        for item in resources
                        if str(item.id) == str(resource.resource_id)
                    ),
                    None,
                )

                if database_resource is None:
                    continue

                record = Recommendation(
                    user_id=user.id,
                    resource_id=database_resource.id,
                    recommendation_type=request.recommendation_type.value,
                    score=ranked_item.score,
                    rank_position=ranked_item.rank_position,
                    reason=explanation.reason,
                    status="generated",
                    algorithm_version=ranked_item.algorithm_version,
                    recommendation_metadata={
                        "explanation": explanation.model_dump(mode="json"),
                        "explanation_version": explanation.explanation_version,
                        "context_version": context.context_version,
                    },
                )

                db.add(record)

                recommendation_records.append(
                    (record, database_resource, explanation)
                )

            db.flush()

            return {
                "request_id": uuid4(),
                "total_results": len(recommendation_records),
                "recommendations": recommendation_records,
                "generated_at": datetime.now(timezone.utc),
                "algorithm_version": self.scoring_service.ALGORITHM_VERSION,
            }

        except Exception:
            db.rollback()
            raise