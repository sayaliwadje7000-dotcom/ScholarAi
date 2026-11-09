import pytest

from datetime import datetime, timezone

from pydantic import ValidationError

from app.schemas.learning_profile import (
    LearningGoalCreate,
    LearningGoalUpdate,
    LearningGoalPriority,
    LearningGoalStatus,
    LearningProfileUpdate,
)


# ============================================================
# GOAL CREATION
# ============================================================


def test_learning_goal_creation():

    goal = LearningGoalCreate(
        title="Master Data Structures",
        description="Study trees, graphs and hashing.",
        subject="Data Structures",
        priority="high",
    )

    assert goal.title == "Master Data Structures"

    assert goal.subject == "Data Structures"

    assert goal.priority == LearningGoalPriority.HIGH

    assert goal.status == LearningGoalStatus.ACTIVE

    assert goal.progress_percent == 0


def test_learning_goal_title_is_required():

    with pytest.raises(ValidationError):

        LearningGoalCreate(
            title="",
        )


def test_learning_goal_title_is_trimmed():

    goal = LearningGoalCreate(
        title="  Learn Python  ",
    )

    assert goal.title == "Learn Python"


def test_learning_goal_invalid_priority():

    with pytest.raises(ValidationError):

        LearningGoalCreate(
            title="Learn Python",
            priority="urgent",
        )


def test_learning_goal_progress_boundary():

    goal = LearningGoalCreate(
        title="Complete Python course",
        progress_percent=75,
    )

    assert goal.progress_percent == 75


def test_learning_goal_rejects_invalid_progress():

    with pytest.raises(ValidationError):

        LearningGoalCreate(
            title="Complete Python course",
            progress_percent=120,
        )


# ============================================================
# GOAL COMPLETION
# ============================================================


def test_completed_goal_sets_progress_to_100():

    goal = LearningGoalCreate(
        title="Complete Python course",
        status="completed",
        progress_percent=60,
    )

    assert goal.status == LearningGoalStatus.COMPLETED

    assert goal.progress_percent == 100


def test_100_percent_progress_completes_goal():

    goal = LearningGoalCreate(
        title="Complete Python course",
        progress_percent=100,
    )

    assert goal.status == LearningGoalStatus.COMPLETED


# ============================================================
# GOAL UPDATES
# ============================================================


def test_learning_goal_partial_update():

    update = LearningGoalUpdate(
        progress_percent=50,
    )

    values = update.model_dump(
        exclude_unset=True,
    )

    assert values == {
        "progress_percent": 50,
    }


def test_learning_goal_empty_update():

    update = LearningGoalUpdate()

    assert update.model_dump(
        exclude_unset=True,
    ) == {}


# ============================================================
# PROFILE VALIDATION
# ============================================================


def test_profile_subject_normalization():

    profile = LearningProfileUpdate(
        preferred_subjects=[
            " Data Structures ",
            "Artificial Intelligence",
            "data structures",
        ],
    )

    assert profile.preferred_subjects == [
        "Data Structures",
        "Artificial Intelligence",
    ]


def test_profile_language_normalization():

    profile = LearningProfileUpdate(
        preferred_language=" English ",
    )

    assert profile.preferred_language == "English"


def test_profile_notification_update():

    profile = LearningProfileUpdate(
        notification_enabled=False,
    )

    assert profile.notification_enabled is False


def test_profile_rejects_unknown_fields():

    with pytest.raises(ValidationError):

        LearningProfileUpdate(
            unknown_field="invalid",
        )