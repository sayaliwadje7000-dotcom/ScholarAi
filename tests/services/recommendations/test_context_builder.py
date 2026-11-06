from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.schemas.recommendations import (
    RecommendationRequest,
)

from app.services.recommendations.context_builder import (
    LearningContextBuilder,
)


@pytest.fixture
def builder():
    return LearningContextBuilder()


@pytest.fixture
def sample_user():
    preferences = SimpleNamespace(
        preferred_language=" English ",
        education_level="Undergraduate",
        preferred_subjects=[
            "Data Structures",
            "Programming",
            "data structures",
        ],
        learning_goals=[
            "Understand algorithms",
            "Improve problem solving",
        ],
    )

    return SimpleNamespace(
        id=uuid4(),
        preferences=preferences,
        resource_interactions=[],
    )


@pytest.fixture
def sample_request():
    return RecommendationRequest(
        query="Learn binary trees",
        subject="Computer Science",
        language="Hindi",
        difficulty_level="beginner",
        resource_types=["video", "article"],
        limit=10,
    )


def test_builder_requires_user(builder):
    with pytest.raises(ValueError, match="authenticated user"):
        builder.build(None)


def test_builder_requires_user_id(builder):
    user = SimpleNamespace(
        preferences=None,
        resource_interactions=[],
    )

    with pytest.raises(ValueError, match="User ID"):
        builder.build(user)


def test_builder_creates_context_without_request(
    builder,
    sample_user,
):
    result = builder.build(sample_user)

    assert result.context_version == "v1"

    assert result.intent.query is None

    assert (
        result.learning_context.preferred_language
        == "english"
    )


def test_builder_extracts_user_id(
    builder,
    sample_user,
):
    result = builder.build(sample_user)

    assert result.learning_context.user_id == sample_user.id


def test_builder_normalizes_preferred_language(
    builder,
    sample_user,
):
    result = builder.build(sample_user)

    assert (
        result.learning_context.preferred_language
        == "english"
    )


def test_builder_normalizes_preferred_subjects(
    builder,
    sample_user,
):
    result = builder.build(sample_user)

    assert result.learning_context.preferred_subjects == [
        "Data Structures",
        "Programming",
    ]


def test_builder_extracts_learning_goals(
    builder,
    sample_user,
):
    result = builder.build(sample_user)

    assert result.learning_context.learning_goals == [
        "Understand algorithms",
        "Improve problem solving",
    ]


def test_builder_extracts_education_level(
    builder,
    sample_user,
):
    result = builder.build(sample_user)

    assert (
        result.learning_context.education_level
        == "Undergraduate"
    )


def test_builder_extracts_request_intent(
    builder,
    sample_user,
    sample_request,
):
    result = builder.build(
        sample_user,
        sample_request,
    )

    assert result.intent.query == "Learn binary trees"

    assert result.intent.subject == "Computer Science"

    assert result.intent.language == "hindi"

    assert result.intent.difficulty_level == "beginner"


def test_request_language_overrides_preference(
    builder,
    sample_user,
    sample_request,
):
    result = builder.build(
        sample_user,
        sample_request,
    )

    assert (
        result.learning_context.preferred_language
        == "hindi"
    )


def test_request_subject_is_added_to_preferred_subjects(
    builder,
    sample_user,
    sample_request,
):
    result = builder.build(
        sample_user,
        sample_request,
    )

    assert result.learning_context.preferred_subjects == [
        "Computer Science",
        "Data Structures",
        "Programming",
    ]


def test_builder_preserves_learning_goals(
    builder,
    sample_user,
    sample_request,
):
    result = builder.build(
        sample_user,
        sample_request,
    )

    assert result.learning_context.learning_goals == [
        "Understand algorithms",
        "Improve problem solving",
    ]


def test_builder_handles_missing_preferences(builder):
    user = SimpleNamespace(
        id=uuid4(),
        preferences=None,
        resource_interactions=[],
    )

    result = builder.build(user)

    assert result.learning_context.preferred_language is None

    assert result.learning_context.education_level is None

    assert result.learning_context.preferred_subjects == []

    assert result.learning_context.learning_goals == []


def test_builder_handles_dictionary_user(builder):
    user = {
        "id": uuid4(),
        "preferences": {
            "preferred_language": "Marathi",
            "education_level": "Undergraduate",
            "preferred_subjects": ["Programming"],
            "learning_goals": ["Learn Python"],
        },
        "resource_interactions": [],
    }

    result = builder.build(user)

    assert (
        result.learning_context.preferred_language
        == "marathi"
    )

    assert result.learning_context.preferred_subjects == [
        "Programming"
    ]


def test_builder_extracts_recent_interactions(
    builder,
    sample_user,
):
    resource_id = uuid4()

    interaction = SimpleNamespace(
        resource_id=resource_id,
        interaction_type="view",
        rating=None,
        duration_seconds=120,
        occurred_at=datetime.now(timezone.utc),
    )

    result = builder.build(
        sample_user,
        interactions=[interaction],
    )

    assert len(
        result.learning_context.recent_interactions
    ) == 1

    summary = result.learning_context.recent_interactions[0]

    assert summary.resource_id == resource_id

    assert summary.duration_seconds == 120


def test_builder_sorts_interactions_newest_first(
    builder,
    sample_user,
):
    now = datetime.now(timezone.utc)

    older = SimpleNamespace(
        resource_id=uuid4(),
        interaction_type="view",
        rating=None,
        duration_seconds=30,
        occurred_at=now - timedelta(days=2),
    )

    newer = SimpleNamespace(
        resource_id=uuid4(),
        interaction_type="save",
        rating=None,
        duration_seconds=0,
        occurred_at=now,
    )

    result = builder.build(
        sample_user,
        interactions=[older, newer],
    )

    interactions = result.learning_context.recent_interactions

    assert interactions[0].resource_id == newer.resource_id

    assert interactions[1].resource_id == older.resource_id


def test_builder_limits_interaction_history(
    sample_user,
):
    builder = LearningContextBuilder(
        max_recent_interactions=2
    )

    now = datetime.now(timezone.utc)

    interactions = []

    for index in range(5):
        interactions.append(
            SimpleNamespace(
                resource_id=uuid4(),
                interaction_type="view",
                rating=None,
                duration_seconds=10,
                occurred_at=now - timedelta(minutes=index),
            )
        )

    result = builder.build(
        sample_user,
        interactions=interactions,
    )

    assert len(
        result.learning_context.recent_interactions
    ) == 2


def test_builder_skips_invalid_interactions(
    builder,
    sample_user,
):
    valid_interaction = SimpleNamespace(
        resource_id=uuid4(),
        interaction_type="view",
        rating=None,
        duration_seconds=60,
        occurred_at=datetime.now(timezone.utc),
    )

    invalid_interaction = SimpleNamespace(
        resource_id=uuid4(),
        interaction_type="invalid",
        rating=None,
        duration_seconds=60,
        occurred_at=datetime.now(timezone.utc),
    )

    result = builder.build(
        sample_user,
        interactions=[
            valid_interaction,
            invalid_interaction,
        ],
    )

    assert len(
        result.learning_context.recent_interactions
    ) == 1


def test_builder_skips_interactions_without_resource_id(
    builder,
    sample_user,
):
    interaction = SimpleNamespace(
        resource_id=None,
        interaction_type="view",
        rating=None,
        duration_seconds=60,
        occurred_at=datetime.now(timezone.utc),
    )

    result = builder.build(
        sample_user,
        interactions=[interaction],
    )

    assert result.learning_context.recent_interactions == []


def test_builder_does_not_modify_user_preferences(
    builder,
    sample_user,
):
    original_subjects = list(
        sample_user.preferences.preferred_subjects
    )

    builder.build(sample_user)

    assert (
        sample_user.preferences.preferred_subjects
        == original_subjects
    )


def test_builder_uses_user_interaction_relationship(
    builder,
    sample_user,
):
    interaction = SimpleNamespace(
        resource_id=uuid4(),
        interaction_type="complete",
        rating=None,
        duration_seconds=300,
        occurred_at=datetime.now(timezone.utc),
    )

    sample_user.resource_interactions = [interaction]

    result = builder.build(sample_user)

    assert len(
        result.learning_context.recent_interactions
    ) == 1


def test_builder_validates_interaction_limit():
    with pytest.raises(ValueError):
        LearningContextBuilder(
            max_recent_interactions=0
        )