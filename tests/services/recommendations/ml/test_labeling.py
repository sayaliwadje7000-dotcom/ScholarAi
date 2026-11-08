from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.services.recommendations.ml.dataset_schema import (
    DatasetLabel,
    LabelSource,
)

from app.services.recommendations.ml.labeling import (
    InteractionSignal,
    LabelPolicy,
    RecommendationFeedbackSignal,
    build_training_examples,
    label_interaction,
    label_recommendation_feedback,
)


NOW = datetime(
    2026,
    11,
    7,
    12,
    0,
    tzinfo=timezone.utc,
)


@pytest.mark.parametrize(
    "event_type",
    ["click", "save", "complete"],
)
def test_strong_positive_interactions(event_type):

    result = label_interaction(
        InteractionSignal(
            uuid4(),
            uuid4(),
            event_type,
            NOW,
        )
    )

    assert result is not None
    assert result.label == DatasetLabel.RELEVANT
    assert result.label_source == LabelSource.INTERACTION


def test_view_is_not_a_label():

    assert label_interaction(
        InteractionSignal(
            uuid4(),
            uuid4(),
            "view",
            NOW,
        )
    ) is None


def test_four_and_five_star_ratings_are_positive():

    for rating in (4, 5):

        result = label_interaction(
            InteractionSignal(
                uuid4(),
                uuid4(),
                "rate",
                NOW,
                rating,
            )
        )

        assert result.label == DatasetLabel.RELEVANT


def test_one_and_two_star_ratings_are_negative():

    for rating in (1, 2):

        result = label_interaction(
            InteractionSignal(
                uuid4(),
                uuid4(),
                "rate",
                NOW,
                rating,
            )
        )

        assert result.label == DatasetLabel.NOT_RELEVANT


def test_three_star_rating_is_neutral():

    assert label_interaction(
        InteractionSignal(
            uuid4(),
            uuid4(),
            "rate",
            NOW,
            3,
        )
    ) is None


def test_rate_without_valid_rating_is_rejected():

    with pytest.raises(
        ValueError,
        match="rating from 1 to 5",
    ):

        label_interaction(
            InteractionSignal(
                uuid4(),
                uuid4(),
                "rate",
                NOW,
                None,
            )
        )


@pytest.mark.parametrize(
    ("feedback", "expected"),
    [
        ("helpful", DatasetLabel.RELEVANT),
        ("not_helpful", DatasetLabel.NOT_RELEVANT),
        ("irrelevant", DatasetLabel.NOT_RELEVANT),
    ],
)
def test_explicit_feedback_mapping(feedback, expected):

    result = label_recommendation_feedback(
        RecommendationFeedbackSignal(
            uuid4(),
            uuid4(),
            feedback,
            NOW,
        )
    )

    assert result.label == expected
    assert result.label_source == LabelSource.EXPLICIT_FEEDBACK


def test_explicit_feedback_overrides_newer_implicit_interaction():

    user_id = uuid4()
    resource_id = uuid4()

    events = [
        RecommendationFeedbackSignal(
            user_id,
            resource_id,
            "not_helpful",
            NOW,
        ),
        InteractionSignal(
            user_id,
            resource_id,
            "save",
            NOW + timedelta(days=1),
        ),
    ]

    result = build_training_examples(events)

    assert len(result) == 1
    assert result[0].label == DatasetLabel.NOT_RELEVANT
    assert result[0].label_source == LabelSource.EXPLICIT_FEEDBACK


def test_latest_event_wins_within_same_source_class():

    user_id = uuid4()
    resource_id = uuid4()

    events = [
        InteractionSignal(
            user_id,
            resource_id,
            "save",
            NOW,
        ),
        InteractionSignal(
            user_id,
            resource_id,
            "rate",
            NOW + timedelta(hours=1),
            1,
        ),
    ]

    result = build_training_examples(events)

    assert len(result) == 1
    assert result[0].label == DatasetLabel.NOT_RELEVANT


def test_unknown_and_view_events_do_not_create_negatives():

    user_id = uuid4()
    resource_id = uuid4()

    result = build_training_examples(
        [
            InteractionSignal(
                user_id,
                resource_id,
                "view",
                NOW,
            )
        ]
    )

    assert result == []


def test_naive_event_timestamp_is_rejected():

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):

        label_interaction(
            InteractionSignal(
                uuid4(),
                uuid4(),
                "click",
                datetime(2026, 1, 1),
            )
        )


def test_invalid_policy_thresholds_are_rejected():

    with pytest.raises(
        ValueError,
        match="rating thresholds",
    ):

        LabelPolicy(
            positive_rating_min=3,
            negative_rating_max=3,
        )