from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.schemas.recommendations import (
    LearningContext,
    RecommendationRequest,
)

from app.schemas.embeddings import EmbeddingResult

from app.services.recommendations.content_based.query_context_service import (
    ContentQueryContextService,
    EmptyLearningIntentError,
    QueryEmbeddingError,
)


class FakeContextBuilder:

    def build(
        self,
        user,
        preferences,
        request,
        interactions,
    ):
        return LearningContext(
            user_id=user.id,
            preferred_language="English",
            education_level="Undergraduate",
            preferred_subjects=["Computer Science"],
            learning_goals=["Learn machine learning"],
        )


class FakeEmbeddingService:

    def __init__(self):
        self.received_text = None

    def embed_query(self, text):
        self.received_text = text

        return EmbeddingResult(
            vector=tuple([0.1] * 1536),
            model="gemini-embedding-2",
            provider="gemini",
            dimensions=1536,
        )


@pytest.fixture
def user():
    return SimpleNamespace(
        id=uuid4(),
        preferences=None,
    )


@pytest.fixture
def recommendation_request():
    return RecommendationRequest(
        query="Deep learning fundamentals",
        subject="Computer Science",
        language="English",
    )


@pytest.fixture
def embedding_service():
    return FakeEmbeddingService()


@pytest.fixture
def context_service(embedding_service):
    return ContentQueryContextService(
        embedding_service=embedding_service,
        context_builder=FakeContextBuilder(),
    )


def test_query_text_includes_explicit_query(
    context_service,
    recommendation_request,
):
    learning_context = LearningContext(
        user_id=uuid4(),
    )

    result = context_service.build_query_text(
        recommendation_request,
        learning_context,
    )

    assert "Deep learning fundamentals" in result


def test_query_text_includes_learning_goals(
    context_service,
    recommendation_request,
):
    learning_context = LearningContext(
        user_id=uuid4(),
        learning_goals=["Learn machine learning"],
    )

    result = context_service.build_query_text(
        recommendation_request,
        learning_context,
    )

    assert "Learn machine learning" in result


def test_query_text_includes_preferred_subjects(
    context_service,
    recommendation_request,
):
    learning_context = LearningContext(
        user_id=uuid4(),
        preferred_subjects=["Computer Science"],
    )

    result = context_service.build_query_text(
        recommendation_request,
        learning_context,
    )

    assert "Computer Science" in result


def test_query_text_rejects_empty_learning_intent(
    context_service,
):
    learning_context = LearningContext(
        user_id=uuid4(),
    )

    request_without_intent = RecommendationRequest()

    with pytest.raises(EmptyLearningIntentError):
        context_service.build_query_text(
            request_without_intent,
            learning_context,
        )


def test_request_language_overrides_preference(
    context_service,
    recommendation_request,
):
    learning_context = LearningContext(
        user_id=uuid4(),
        preferred_language="Hindi",
    )

    filters = context_service.build_filters(
        recommendation_request,
        learning_context,
    )

    assert filters.language == "english"


def test_preferred_language_is_used_when_request_language_missing(
    context_service,
):
    request_without_language = RecommendationRequest(
        query="Python programming",
    )

    learning_context = LearningContext(
        user_id=uuid4(),
        preferred_language="Hindi",
    )

    filters = context_service.build_filters(
        request_without_language,
        learning_context,
    )

    assert filters.language == "Hindi"


@pytest.mark.asyncio
async def test_build_generates_query_embedding(
    context_service,
    user,
    recommendation_request,
    embedding_service,
):
    result = await context_service.build(
        user=user,
        request=recommendation_request,
    )

    assert len(result.query_embedding) == 1536
    assert result.embedding_provider == "gemini"
    assert result.embedding_model == "gemini-embedding-2"
    assert embedding_service.received_text == result.query_text


@pytest.mark.asyncio
async def test_build_preserves_user_identity(
    context_service,
    user,
    recommendation_request,
):
    result = await context_service.build(
        user=user,
        request=recommendation_request,
    )

    assert result.user_id == user.id
    assert result.learning_context.user_id == user.id


@pytest.mark.asyncio
async def test_build_preserves_learning_context(
    context_service,
    user,
    recommendation_request,
):
    result = await context_service.build(
        user=user,
        request=recommendation_request,
    )

    assert (
        "Learn machine learning"
        in result.learning_context.learning_goals
    )


@pytest.mark.asyncio
async def test_embedding_failure_is_wrapped(
    user,
    recommendation_request,
):

    class BrokenEmbeddingService:

        def embed_query(self, text):
            raise RuntimeError("Provider unavailable")

    service = ContentQueryContextService(
        embedding_service=BrokenEmbeddingService(),
        context_builder=FakeContextBuilder(),
    )

    with pytest.raises(QueryEmbeddingError):
        await service.build(
            user=user,
            request=recommendation_request,
        )


@pytest.mark.asyncio
async def test_invalid_embedding_dimensions_are_rejected(
    user,
    recommendation_request,
):

    class InvalidEmbeddingService:

        def embed_query(self, text):
            return EmbeddingResult(
                vector=tuple([0.1] * 768),
                model="gemini-embedding-2",
                provider="gemini",
                dimensions=768,
            )

    service = ContentQueryContextService(
        embedding_service=InvalidEmbeddingService(),
        context_builder=FakeContextBuilder(),
    )

    with pytest.raises(QueryEmbeddingError):
        await service.build(
            user=user,
            request=recommendation_request,
        )


@pytest.mark.asyncio
async def test_embedding_service_is_not_called_without_intent(
    user,
):

    class TrackingEmbeddingService:

        def __init__(self):
            self.called = False

        def embed_query(self, text):
            self.called = True

            raise AssertionError(
                "Embedding must not be called."
            )

    embedding = TrackingEmbeddingService()

    class EmptyContextBuilder:

        def build(
            self,
            user,
            preferences,
            request,
            interactions,
        ):
            return LearningContext(
                user_id=user.id,
            )

    service = ContentQueryContextService(
        embedding_service=embedding,
        context_builder=EmptyContextBuilder(),
    )

    with pytest.raises(EmptyLearningIntentError):
        await service.build(
            user=user,
            request=RecommendationRequest(),
        )

    assert embedding.called is False