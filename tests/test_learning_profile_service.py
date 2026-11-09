import uuid

from app.services.learning_profile_service import (
    LearningProfileService,
)


def test_legacy_goal_conversion():

    user_id = uuid.uuid4()

    result = LearningProfileService._convert_legacy_goal(
        user_id=user_id,
        value="Learn Python",
    )

    assert result is not None

    assert result["title"] == "Learn Python"

    assert result["status"] == "active"

    assert result["priority"] == "medium"

    assert result["progress_percent"] == 0


def test_legacy_goal_conversion_is_deterministic():

    user_id = uuid.uuid4()

    first = LearningProfileService._convert_legacy_goal(
        user_id,
        "Learn Python",
    )

    second = LearningProfileService._convert_legacy_goal(
        user_id,
        "Learn Python",
    )

    assert first["id"] == second["id"]


def test_empty_legacy_goal_is_ignored():

    result = LearningProfileService._convert_legacy_goal(
        uuid.uuid4(),
        "   ",
    )

    assert result is None


def test_structured_goal_is_preserved():

    goal = {
        "id": str(uuid.uuid4()),
        "title": "Learn Python",
        "status": "active",
    }

    result = LearningProfileService._convert_legacy_goal(
        uuid.uuid4(),
        goal,
    )

    assert result == goal