from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.learning_activity import LearningActivity

from app.models.user_resource_interaction import (
    UserResourceInteraction,
)

from app.schemas.behavioral_signals import (
    BehavioralSignal,
    BehavioralSignalSource,
    LearningActivityType,
    BehavioralSignalCollection,
)


class BehavioralSignalService:
    """
    Converts existing learning activities and resource
    interactions into normalized behavioral signals.

    This service does not modify recommendation scores.

    It provides structured behavioral evidence for
    subsequent personalization phases.
    """

    DEFAULT_LIMIT = 100

    # ========================================================
    # RESOURCE INTERACTION SIGNAL CONFIGURATION
    # ========================================================

    INTERACTION_WEIGHTS = {

        "view": {
            "strength": 0.10,
            "confidence": 0.30,
        },

        "click": {
            "strength": 0.25,
            "confidence": 0.45,
        },

        "save": {
            "strength": 0.75,
            "confidence": 0.85,
        },

        "complete": {
            "strength": 1.00,
            "confidence": 0.95,
        },
    }

    # ========================================================
    # LEARNING ACTIVITY SIGNAL CONFIGURATION
    # ========================================================

    ACTIVITY_WEIGHTS = {

        LearningActivityType.DOCUMENT_UPLOADED.value: {
            "strength": 0.20,
            "confidence": 0.40,
        },

        LearningActivityType.STUDY_SESSION_STARTED.value: {
            "strength": 0.25,
            "confidence": 0.45,
        },

        LearningActivityType.STUDY_SESSION_COMPLETED.value: {
            "strength": 0.70,
            "confidence": 0.80,
        },

        LearningActivityType.AI_QUESTION_ASKED.value: {
            "strength": 0.35,
            "confidence": 0.50,
        },

        LearningActivityType.QUIZ_ATTEMPTED.value: {
            "strength": 0.30,
            "confidence": 0.45,
        },

        LearningActivityType.QUIZ_COMPLETED.value: {
            "strength": 0.75,
            "confidence": 0.80,
        },

        LearningActivityType.SEARCH_PERFORMED.value: {
            "strength": 0.15,
            "confidence": 0.30,
        },

        LearningActivityType.RESOURCE_RECOMMENDED.value: {
            "strength": 0.00,
            "confidence": 0.00,
        },
    }

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __init__(
        self,
        max_signals: int = DEFAULT_LIMIT,
    ):

        if (
            isinstance(max_signals, bool)
            or not isinstance(max_signals, int)
            or max_signals < 1
        ):
            raise ValueError(
                "max_signals must be a positive integer."
            )

        self.max_signals = max_signals

    # ========================================================
    # TIMESTAMP NORMALIZATION
    # ========================================================

    @staticmethod
    def normalize_timestamp(value):

        if not isinstance(value, datetime):
            return datetime.min.replace(
                tzinfo=timezone.utc
            )

        if value.tzinfo is None:
            return value.replace(
                tzinfo=timezone.utc
            )

        return value.astimezone(timezone.utc)

    # ========================================================
    # RESOURCE INTERACTION SIGNAL
    # ========================================================

    def process_resource_interaction(
        self,
        interaction: UserResourceInteraction,
    ) -> BehavioralSignal | None:

        interaction_type = interaction.interaction_type

        if interaction_type == "rate":

            rating = interaction.rating

            if rating is None:
                return None

            # Convert rating 1–5 to signal -1.0–1.0.
            strength = (rating - 3) / 2

            return BehavioralSignal(
                source=(
                    BehavioralSignalSource.RESOURCE_INTERACTION
                ),
                source_event_id=interaction.id,
                event_type="rate",
                entity_type="study_resource",
                entity_id=interaction.resource_id,
                resource_id=interaction.resource_id,
                signal_strength=strength,
                confidence=0.95,
                duration_seconds=interaction.duration_seconds,
                occurred_at=self.normalize_timestamp(
                    interaction.occurred_at
                ),
                metadata={
                    "rating": rating,
                },
            )

        configuration = self.INTERACTION_WEIGHTS.get(
            interaction_type
        )

        if configuration is None:
            return None

        metadata = interaction.interaction_metadata or {}

        return BehavioralSignal(
            source=(
                BehavioralSignalSource.RESOURCE_INTERACTION
            ),
            source_event_id=interaction.id,
            event_type=interaction_type,
            entity_type="study_resource",
            entity_id=interaction.resource_id,
            resource_id=interaction.resource_id,
            signal_strength=configuration["strength"],
            confidence=configuration["confidence"],
            duration_seconds=interaction.duration_seconds,
            occurred_at=self.normalize_timestamp(
                interaction.occurred_at
            ),
            metadata=metadata,
        )

    # ========================================================
    # LEARNING ACTIVITY SIGNAL
    # ========================================================

    def process_learning_activity(
        self,
        activity: LearningActivity,
    ) -> BehavioralSignal | None:

        activity_type = activity.activity_type

        configuration = self.ACTIVITY_WEIGHTS.get(
            activity_type
        )

        if configuration is None:
            return None

        # Events without behavioral evidence do not
        # become recommendation signals.
        if configuration["confidence"] == 0:
            return None

        metadata = activity.activity_metadata or {}

        return BehavioralSignal(
            source=(
                BehavioralSignalSource.LEARNING_ACTIVITY
            ),
            source_event_id=activity.id,
            event_type=activity_type,
            entity_type=activity.entity_type,
            entity_id=activity.entity_id,
            resource_id=(
                activity.entity_id
                if activity.entity_type == "study_resource"
                else None
            ),
            signal_strength=configuration["strength"],
            confidence=configuration["confidence"],
            duration_seconds=activity.duration_seconds,
            occurred_at=self.normalize_timestamp(
                activity.occurred_at
            ),
            metadata=metadata,
        )

    # ========================================================
    # LOAD LEARNING ACTIVITIES
    # ========================================================

    def load_learning_activities(
        self,
        db: Session,
        user_id: UUID,
    ):

        statement = (
            select(LearningActivity)
            .where(
                LearningActivity.user_id == user_id
            )
            .order_by(
                LearningActivity.occurred_at.desc(),
                LearningActivity.id.desc(),
            )
            .limit(self.max_signals)
        )

        return list(
            db.scalars(statement).all()
        )

    # ========================================================
    # LOAD RESOURCE INTERACTIONS
    # ========================================================

    def load_resource_interactions(
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
                UserResourceInteraction.occurred_at.desc(),
                UserResourceInteraction.id.desc(),
            )
            .limit(self.max_signals)
        )

        return list(
            db.scalars(statement).all()
        )

    # ========================================================
    # BUILD BEHAVIORAL SIGNAL COLLECTION
    # ========================================================

    def build_signals(
        self,
        db: Session,
        user_id: UUID,
    ) -> BehavioralSignalCollection:

        activities = self.load_learning_activities(
            db=db,
            user_id=user_id,
        )

        interactions = self.load_resource_interactions(
            db=db,
            user_id=user_id,
        )

        activity_signals = []

        interaction_signals = []

        for activity in activities:

            signal = self.process_learning_activity(
                activity
            )

            if signal is not None:
                activity_signals.append(signal)

        for interaction in interactions:

            signal = self.process_resource_interaction(
                interaction
            )

            if signal is not None:
                interaction_signals.append(signal)

        combined_signals = (
            activity_signals + interaction_signals
        )

        combined_signals.sort(
            key=lambda signal: (
                signal.occurred_at,
                str(signal.source_event_id),
            ),
            reverse=True,
        )

        combined_signals = combined_signals[
            :self.max_signals
        ]

        return BehavioralSignalCollection(
            user_id=user_id,
            total_signals=len(combined_signals),
            activity_signals=len(activity_signals),
            interaction_signals=len(interaction_signals),
            signals=combined_signals,
            generated_at=datetime.now(timezone.utc),
        )

    # ========================================================
    # RECORD LEARNING ACTIVITY
    # ========================================================

    def record_activity(
        self,
        db: Session,
        user_id: UUID,
        request,
    ) -> LearningActivity:

        activity = LearningActivity(
            user_id=user_id,
            activity_type=request.activity_type.value,
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            duration_seconds=request.duration_seconds,
            activity_metadata=request.activity_metadata,
        )

        db.add(activity)

        db.flush()

        return activity