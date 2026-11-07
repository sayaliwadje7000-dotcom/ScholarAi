import pytest

from types import SimpleNamespace

from sqlalchemy.dialects import postgresql
from sqlalchemy import select

from app.models.resource_embedding import ResourceEmbedding
from app.models.study_resource import StudyResource

from app.services.recommendations.content_based.similarity_service import (
    ResourceSimilarityService,
    ResourceSimilarityValidationError,
)


@pytest.fixture
def similarity_service():

    settings = SimpleNamespace(
        provider="gemini",
        model="gemini-embedding-2",
        dimensions=1536,
    )

    return ResourceSimilarityService(
        settings=settings,
    )


def test_valid_vector_is_accepted(similarity_service):

    vector = [0.1] * 1536

    result = similarity_service.validate_vector(vector)

    assert len(result) == 1536
    assert result[0] == 0.1


def test_invalid_vector_dimension_is_rejected(similarity_service):

    with pytest.raises(ResourceSimilarityValidationError):
        similarity_service.validate_vector([0.1] * 100)


def test_non_finite_vector_value_is_rejected(similarity_service):

    vector = [0.1] * 1536
    vector[10] = float("nan")

    with pytest.raises(ResourceSimilarityValidationError):
        similarity_service.validate_vector(vector)


def test_infinite_vector_value_is_rejected(similarity_service):

    vector = [0.1] * 1536
    vector[10] = float("inf")

    with pytest.raises(ResourceSimilarityValidationError):
        similarity_service.validate_vector(vector)


def test_boolean_vector_value_is_rejected(similarity_service):

    vector = [0.1] * 1536
    vector[10] = True

    with pytest.raises(ResourceSimilarityValidationError):
        similarity_service.validate_vector(vector)


def test_string_vector_is_rejected(similarity_service):

    with pytest.raises(ResourceSimilarityValidationError):
        similarity_service.validate_vector("invalid")


@pytest.mark.parametrize(
    ("distance", "expected"),
    [
        (0.0, 1.0),
        (0.1, 0.9),
        (0.25, 0.75),
        (0.5, 0.5),
        (1.0, 0.0),
        (1.5, -0.5),
        (2.0, -1.0),
    ],
)
def test_distance_to_similarity(
    similarity_service,
    distance,
    expected,
):

    result = similarity_service.distance_to_similarity(distance)

    assert result == pytest.approx(expected)


@pytest.mark.parametrize(
    "distance",
    [
        -0.1,
        2.1,
        float("nan"),
        float("inf"),
    ],
)
def test_invalid_distance_is_rejected(
    similarity_service,
    distance,
):

    with pytest.raises(ResourceSimilarityValidationError):
        similarity_service.distance_to_similarity(distance)


def test_invalid_limit_is_rejected(similarity_service):

    with pytest.raises(ResourceSimilarityValidationError):
        similarity_service.find_similar_resources(
            db=None,
            query_vector=[0.1] * 1536,
            limit=0,
        )


def test_boolean_limit_is_rejected(similarity_service):

    with pytest.raises(ResourceSimilarityValidationError):
        similarity_service.find_similar_resources(
            db=None,
            query_vector=[0.1] * 1536,
            limit=True,
        )


def test_invalid_similarity_threshold_is_rejected(
    similarity_service,
):

    with pytest.raises(ResourceSimilarityValidationError):
        similarity_service.find_similar_resources(
            db=None,
            query_vector=[0.1] * 1536,
            min_similarity=1.5,
        )


def test_embedding_compatibility_filters(similarity_service):

    filters = similarity_service._compatible_embedding_filters()

    assert len(filters) == 5


def test_similarity_query_compiles_for_postgresql(
    similarity_service,
):

    vector = [0.1] * 1536

    distance_expression = (
        ResourceEmbedding.embedding.cosine_distance(vector)
    )

    statement = (
        select(
            StudyResource,
            ResourceEmbedding.id.label("embedding_id"),
            distance_expression.label("cosine_distance"),
        )
        .join(
            ResourceEmbedding,
            ResourceEmbedding.resource_id == StudyResource.id,
        )
        .where(
            StudyResource.is_active.is_(True),
            *similarity_service._compatible_embedding_filters(),
        )
        .order_by(distance_expression.asc())
        .limit(10)
    )

    compiled = str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": False},
        )
    )

    assert "study_resources" in compiled
    assert "resource_embeddings" in compiled
    assert "ORDER BY" in compiled
    assert "LIMIT" in compiled


def test_invalid_settings_dimensions_are_rejected():

    settings = SimpleNamespace(
        provider="gemini",
        model="gemini-embedding-2",
        dimensions=768,
    )

    with pytest.raises(ResourceSimilarityValidationError):
        ResourceSimilarityService(settings=settings)