from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.embeddings.resource_embedding_pipeline import (
    ResourceEmbeddingPipeline,
)


class FakeEmbeddingService:

    def __init__(self):

        self.settings = SimpleNamespace(
            provider="gemini",
            model="gemini-embedding-2",
        )

    async def embed_document(self, text):

        return SimpleNamespace(
            vector=[0.1] * 1536,
            dimensions=1536,
            provider="gemini",
            model="gemini-embedding-2",
        )


@pytest.fixture
def resource():

    return SimpleNamespace(
        id=uuid4(),
        title="Python Programming",
        description="Learn Python programming.",
        resource_type="course",
        provider="Example",
        subject="Computer Science",
        language="English",
        difficulty_level="beginner",
        resource_metadata={
            "topics": ["Python"],
            "keywords": ["Programming"],
        },
        categories=[],
    )


@pytest.mark.asyncio
async def test_pipeline_generates_embedding(resource):

    service = FakeEmbeddingService()

    pipeline = ResourceEmbeddingPipeline(
        embedding_service=service,
    )

    result = await pipeline.generate([resource])

    assert result.total_resources == 1

    assert result.successful_resources == 1

    assert result.failed_resources == 0

    outcome = result.outcomes[0]

    assert outcome.status == "ready"

    assert outcome.embedding.dimensions == 1536


@pytest.mark.asyncio
async def test_pipeline_handles_empty_input():

    service = FakeEmbeddingService()

    pipeline = ResourceEmbeddingPipeline(
        embedding_service=service,
    )

    result = await pipeline.generate([])

    assert result.total_resources == 0

    assert result.success_rate == 0.0


@pytest.mark.asyncio
async def test_pipeline_rejects_invalid_input():

    service = FakeEmbeddingService()

    pipeline = ResourceEmbeddingPipeline(
        embedding_service=service,
    )

    with pytest.raises(TypeError):

        await pipeline.generate("invalid")


@pytest.mark.asyncio
async def test_pipeline_records_provider_failure(resource):

    class FailingEmbeddingService(FakeEmbeddingService):

        async def embed_document(self, text):

            raise RuntimeError("Provider unavailable")

    pipeline = ResourceEmbeddingPipeline(
        embedding_service=FailingEmbeddingService(),
    )

    result = await pipeline.generate([resource])

    assert result.failed_resources == 1

    assert result.successful_resources == 0

    assert result.outcomes[0].status == "failed"

    assert result.outcomes[0].error_code == "RuntimeError"