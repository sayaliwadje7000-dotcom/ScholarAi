from types import SimpleNamespace

import pytest

from app.core.embedding_config import EmbeddingSettings

from app.schemas.embeddings import (
    EmbeddingRequest,
    EmbeddingTask,
)

from app.services.embeddings.gemini_provider import (
    GeminiEmbeddingProvider,
)

from app.services.embeddings.exceptions import (
    EmbeddingAuthenticationError,
    EmbeddingValidationError,
)


class FakeModels:

    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    async def embed_content(self, **kwargs):
        self.calls.append(kwargs)

        if self.error:
            raise self.error

        return self.response


class FakeClient:

    def __init__(self, models):
        self.aio = SimpleNamespace(
            models=models
        )


@pytest.fixture
def settings():
    return EmbeddingSettings(
        dimensions=768,
        api_key="test-key",
        max_retries=0,
    )


@pytest.mark.asyncio
async def test_successful_embedding(settings):

    models = FakeModels(
        response=SimpleNamespace(
            embeddings=[
                SimpleNamespace(
                    values=[0.1] * 768
                )
            ]
        )
    )

    provider = GeminiEmbeddingProvider(
        settings,
        client=FakeClient(models),
    )

    result = await provider.embed(
        EmbeddingRequest(
            text="Machine learning fundamentals",
            task=EmbeddingTask.DOCUMENT,
        )
    )

    assert len(result.vector) == 768
    assert result.provider == "gemini"

    call = models.calls[0]

    assert call["model"] == "gemini-embedding-2"

    assert call["contents"] == (
    "title: none | text: Machine learning fundamentals"
)


@pytest.mark.asyncio
async def test_query_instruction(settings):

    models = FakeModels(
        response=SimpleNamespace(
            embeddings=[
                SimpleNamespace(
                    values=[0.2] * 768
                )
            ]
        )
    )

    provider = GeminiEmbeddingProvider(
        settings,
        client=FakeClient(models),
    )

    await provider.embed(
        EmbeddingRequest(
            text="What is machine learning?",
            task=EmbeddingTask.QUERY,
        )
    )

    assert (
        "task: search result | query:"
        in models.calls[0]["contents"]
    )


@pytest.mark.asyncio
async def test_invalid_dimension_rejected(settings):

    models = FakeModels(
        response=SimpleNamespace(
            embeddings=[
                SimpleNamespace(
                    values=[0.1] * 100
                )
            ]
        )
    )

    provider = GeminiEmbeddingProvider(
        settings,
        client=FakeClient(models),
    )

    with pytest.raises(EmbeddingValidationError):
        await provider.embed(
            EmbeddingRequest(
                text="Example",
                task=EmbeddingTask.DOCUMENT,
            )
        )


@pytest.mark.asyncio
async def test_non_finite_vector_rejected(settings):

    values = [0.1] * 768
    values[0] = float("nan")

    models = FakeModels(
        response=SimpleNamespace(
            embeddings=[
                SimpleNamespace(values=values)
            ]
        )
    )

    provider = GeminiEmbeddingProvider(
        settings,
        client=FakeClient(models),
    )

    with pytest.raises(EmbeddingValidationError):
        await provider.embed(
            EmbeddingRequest(
                text="Example",
                task=EmbeddingTask.DOCUMENT,
            )
        )


def test_missing_api_key_rejected():

    settings = EmbeddingSettings(
        api_key=None
    )

    with pytest.raises(EmbeddingAuthenticationError):
        GeminiEmbeddingProvider(settings)