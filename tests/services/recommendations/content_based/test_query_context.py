from uuid import uuid4

import pytest

from app.schemas.recommendations import LearningContext

from app.services.recommendations.content_based.query_context import (
    ContentQueryContext,
    ContentQueryFilters,
    QueryContextValidationError,
)


@pytest.fixture
def learning_context():
    return LearningContext(
        user_id=uuid4(),
        preferred_language="English",
        education_level="Undergraduate",
        preferred_subjects=["Computer Science"],
        learning_goals=["Learn machine learning"],
    )


def test_query_filters_normalize_strings():
    filters = ContentQueryFilters(
        subject=" Computer Science ",
        language=" English ",
        resource_types=("video", "tutorial"),
    )

    assert filters.subject == "Computer Science"
    assert filters.language == "English"
    assert filters.resource_types == ("video", "tutorial")


def test_query_filters_remove_duplicates():
    filters = ContentQueryFilters(
        preferred_subjects=(
            "Computer Science",
            "Computer Science",
        ),
    )

    assert filters.preferred_subjects == ("Computer Science",)


def test_query_filters_reject_invalid_boolean():
    with pytest.raises(QueryContextValidationError):
        ContentQueryFilters(
            exclude_completed="yes",
        )


def test_query_filters_reject_non_string_values():
    with pytest.raises(QueryContextValidationError):
        ContentQueryFilters(
            resource_types=(123,),
        )


def test_query_context_rejects_empty_query(learning_context):
    with pytest.raises(QueryContextValidationError):
        ContentQueryContext(
            user_id=learning_context.user_id,
            query_text=" ",
            query_embedding=(0.1,) * 1536,
            learning_context=learning_context,
            filters=ContentQueryFilters(),
            embedding_provider="gemini",
            embedding_model="gemini-embedding-2",
            embedding_dimensions=1536,
        )


def test_query_context_rejects_invalid_dimensions(
    learning_context,
):
    with pytest.raises(QueryContextValidationError):
        ContentQueryContext(
            user_id=learning_context.user_id,
            query_text="Machine learning",
            query_embedding=(0.1,) * 768,
            learning_context=learning_context,
            filters=ContentQueryFilters(),
            embedding_provider="gemini",
            embedding_model="gemini-embedding-2",
            embedding_dimensions=1536,
        )


def test_query_context_rejects_non_finite_values(
    learning_context,
):
    vector = [0.1] * 1536
    vector[10] = float("nan")

    with pytest.raises(QueryContextValidationError):
        ContentQueryContext(
            user_id=learning_context.user_id,
            query_text="Machine learning",
            query_embedding=tuple(vector),
            learning_context=learning_context,
            filters=ContentQueryFilters(),
            embedding_provider="gemini",
            embedding_model="gemini-embedding-2",
            embedding_dimensions=1536,
        )


def test_query_context_rejects_different_user(
    learning_context,
):
    with pytest.raises(QueryContextValidationError):
        ContentQueryContext(
            user_id=uuid4(),
            query_text="Machine learning",
            query_embedding=(0.1,) * 1536,
            learning_context=learning_context,
            filters=ContentQueryFilters(),
            embedding_provider="gemini",
            embedding_model="gemini-embedding-2",
            embedding_dimensions=1536,
        )