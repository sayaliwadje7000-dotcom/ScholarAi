import uuid

from datetime import datetime, timezone

from types import SimpleNamespace

from app.services.behavioral_signal_service import (
    BehavioralSignalService,
)

from app.schemas.behavioral_signals import (
    BehavioralSignalSource,
)


service = BehavioralSignalService()


def make_interaction(
    interaction_type,
    rating=None,
):

    return SimpleNamespace(
        id=uuid.uuid4(),
        resource_id=uuid.uuid4(),
        interaction_type=interaction_type,
        rating=rating,
        duration_seconds=120,
        interaction_metadata={},
        occurred_at=datetime.now(timezone.utc),
    )


def make_activity(activity_type):

    return SimpleNamespace(
        id=uuid.uuid4(),
        activity_type=activity_type,
        entity_type=None,
        entity_id=None,
        duration_seconds=300,
        activity_metadata={},
        occurred_at=datetime.now(timezone.utc),
    )


# ============================================================
# RESOURCE INTERACTION TESTS
# ============================================================


def test_view_generates_weak_positive_signal():

    interaction = make_interaction("view")

    signal = service.process_resource_interaction(
        interaction
    )

    assert signal is not None

    assert signal.signal_strength == 0.10

    assert signal.confidence == 0.30


def test_click_generates_positive_signal():

    interaction = make_interaction("click")

    signal = service.process_resource_interaction(
        interaction
    )

    assert signal.signal_strength == 0.25


def test_save_generates_strong_positive_signal():

    interaction = make_interaction("save")

    signal = service.process_resource_interaction(
        interaction
    )

    assert signal.signal_strength == 0.75

    assert signal.confidence == 0.85


def test_complete_generates_strongest_positive_signal():

    interaction = make_interaction("complete")

    signal = service.process_resource_interaction(
        interaction
    )

    assert signal.signal_strength == 1.0

    assert signal.confidence == 0.95


def test_rating_five_generates_positive_signal():

    interaction = make_interaction(
        "rate",
        rating=5,
    )

    signal = service.process_resource_interaction(
        interaction
    )

    assert signal.signal_strength == 1.0


def test_rating_three_generates_neutral_signal():

    interaction = make_interaction(
        "rate",
        rating=3,
    )

    signal = service.process_resource_interaction(
        interaction
    )

    assert signal.signal_strength == 0.0


def test_rating_one_generates_negative_signal():

    interaction = make_interaction(
        "rate",
        rating=1,
    )

    signal = service.process_resource_interaction(
        interaction
    )

    assert signal.signal_strength == -1.0


def test_unknown_interaction_is_ignored():

    interaction = make_interaction("unknown")

    signal = service.process_resource_interaction(
        interaction
    )

    assert signal is None


# ============================================================
# LEARNING ACTIVITY TESTS
# ============================================================


def test_completed_study_session_generates_signal():

    activity = make_activity(
        "study_session_completed"
    )

    signal = service.process_learning_activity(
        activity
    )

    assert signal is not None

    assert signal.signal_strength == 0.70

    assert signal.confidence == 0.80


def test_ai_question_generates_signal():

    activity = make_activity(
        "ai_question_asked"
    )

    signal = service.process_learning_activity(
        activity
    )

    assert signal is not None

    assert signal.signal_strength == 0.35


def test_resource_recommended_does_not_generate_signal():

    activity = make_activity(
        "resource_recommended"
    )

    signal = service.process_learning_activity(
        activity
    )

    assert signal is None


def test_unknown_activity_is_ignored():

    activity = make_activity(
        "unknown_activity"
    )

    signal = service.process_learning_activity(
        activity
    )

    assert signal is None


# ============================================================
# SIGNAL STRUCTURE
# ============================================================


def test_signal_has_correct_source():

    interaction = make_interaction("save")

    signal = service.process_resource_interaction(
        interaction
    )

    assert (
        signal.source
        == BehavioralSignalSource.RESOURCE_INTERACTION
    )


def test_signal_contains_resource_id():

    interaction = make_interaction("save")

    signal = service.process_resource_interaction(
        interaction
    )

    assert signal.resource_id == interaction.resource_id


def test_signal_strength_is_normalized():

    interaction = make_interaction(
        "rate",
        rating=4,
    )

    signal = service.process_resource_interaction(
        interaction
    )

    assert -1.0 <= signal.signal_strength <= 1.0


def test_signal_confidence_is_normalized():

    interaction = make_interaction("save")

    signal = service.process_resource_interaction(
        interaction
    )

    assert 0.0 <= signal.confidence <= 1.0


# ============================================================
# SERVICE CONFIGURATION
# ============================================================


def test_service_rejects_invalid_limit():

    import pytest

    with pytest.raises(ValueError):

        BehavioralSignalService(
            max_signals=0
        )


def test_service_accepts_custom_limit():

    custom_service = BehavioralSignalService(
        max_signals=50
    )

    assert custom_service.max_signals == 50