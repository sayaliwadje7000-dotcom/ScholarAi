"""Conservative conversion of observed events into relevance labels."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable
from uuid import UUID

from app.services.recommendations.ml.dataset_schema import (
    DatasetLabel,
    LabelSource,
    RecommendationTrainingExample,
)


@dataclass(frozen=True, slots=True)
class LabelPolicy:
    """Configuration for converting user events into labels."""

    positive_rating_min: int = 4
    negative_rating_max: int = 2

    positive_confidence: float = 1.0
    negative_confidence: float = 1.0

    def __post_init__(self) -> None:

        if not (
            1 <= self.negative_rating_max
            < self.positive_rating_min <= 5
        ):
            raise ValueError(
                "rating thresholds must leave a neutral interval"
            )

        for value in (
            self.positive_confidence,
            self.negative_confidence,
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    "confidence values must be between 0 and 1"
                )


@dataclass(frozen=True, slots=True)
class InteractionSignal:

    user_id: UUID
    resource_id: UUID
    interaction_type: str
    occurred_at: datetime
    rating: int | None = None


@dataclass(frozen=True, slots=True)
class RecommendationFeedbackSignal:

    user_id: UUID
    resource_id: UUID
    feedback_type: str
    created_at: datetime


def _validate_timestamp(value: datetime) -> None:

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(
            "event timestamps must be timezone-aware"
        )


def label_interaction(
    event: InteractionSignal,
    policy: LabelPolicy = LabelPolicy(),
) -> RecommendationTrainingExample | None:
    """Convert a supported interaction into a training example."""

    _validate_timestamp(event.occurred_at)

    event_type = event.interaction_type.strip().lower()

    if event_type in {"click", "save", "complete"}:

        return RecommendationTrainingExample(
            user_id=event.user_id,
            resource_id=event.resource_id,
            label=DatasetLabel.RELEVANT,
            label_source=LabelSource.INTERACTION,
            source_event=event_type,
            observed_at=event.occurred_at,
            confidence=policy.positive_confidence,
        )

    if event_type == "rate":

        if event.rating is None or not 1 <= event.rating <= 5:
            raise ValueError(
                "rate interactions require a rating from 1 to 5"
            )

        if event.rating >= policy.positive_rating_min:

            label = DatasetLabel.RELEVANT
            confidence = policy.positive_confidence

        elif event.rating <= policy.negative_rating_max:

            label = DatasetLabel.NOT_RELEVANT
            confidence = policy.negative_confidence

        else:
            return None

        return RecommendationTrainingExample(
            user_id=event.user_id,
            resource_id=event.resource_id,
            label=label,
            label_source=LabelSource.INTERACTION,
            source_event=f"rating_{event.rating}",
            observed_at=event.occurred_at,
            confidence=confidence,
        )

    # Views and unknown interactions are not sufficient evidence.
    return None


def label_recommendation_feedback(
    event: RecommendationFeedbackSignal,
    policy: LabelPolicy = LabelPolicy(),
) -> RecommendationTrainingExample | None:
    """Convert explicit recommendation feedback into labels."""

    _validate_timestamp(event.created_at)

    feedback = event.feedback_type.strip().lower()

    if feedback == "helpful":

        label = DatasetLabel.RELEVANT
        confidence = policy.positive_confidence

    elif feedback in {"not_helpful", "irrelevant"}:

        label = DatasetLabel.NOT_RELEVANT
        confidence = policy.negative_confidence

    else:
        return None

    return RecommendationTrainingExample(
        user_id=event.user_id,
        resource_id=event.resource_id,
        label=label,
        label_source=LabelSource.EXPLICIT_FEEDBACK,
        source_event=feedback,
        observed_at=event.created_at,
        confidence=confidence,
    )


def build_training_examples(
    events: Iterable[
        InteractionSignal | RecommendationFeedbackSignal
    ],
    policy: LabelPolicy = LabelPolicy(),
) -> list[RecommendationTrainingExample]:
    """Build one strongest/latest label per user-resource pair."""

    candidates: dict[
        tuple[UUID, UUID],
        RecommendationTrainingExample,
    ] = {}

    for event in events:

        if isinstance(event, InteractionSignal):

            example = label_interaction(event, policy)

        elif isinstance(event, RecommendationFeedbackSignal):

            example = label_recommendation_feedback(event, policy)

        else:

            raise TypeError(
                f"unsupported event type: {type(event).__name__}"
            )

        if example is None:
            continue

        current = candidates.get(example.sample_key)

        if current is None:
            candidates[example.sample_key] = example
            continue

        current_priority = (
            current.label_source == LabelSource.EXPLICIT_FEEDBACK,
            current.observed_at,
            current.source_event,
        )

        candidate_priority = (
            example.label_source == LabelSource.EXPLICIT_FEEDBACK,
            example.observed_at,
            example.source_event,
        )

        if candidate_priority > current_priority:
            candidates[example.sample_key] = example

    return sorted(
        candidates.values(),
        key=lambda item: (
            item.observed_at,
            str(item.user_id),
            str(item.resource_id),
        ),
    )