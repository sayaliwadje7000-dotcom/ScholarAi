import asyncio

from app.core.embedding_config import (
    EmbeddingSettings,
    get_embedding_settings,
)

from app.schemas.embeddings import (
    EmbeddingRequest,
    EmbeddingResult,
    EmbeddingTask,
)

from app.services.embeddings.base import BaseEmbeddingProvider

from app.services.embeddings.exceptions import (
    EmbeddingInputTooLargeError,
)

from app.services.embeddings.gemini_provider import (
    GeminiEmbeddingProvider,
)


class EmbeddingService:

    def __init__(
        self,
        provider: BaseEmbeddingProvider | None = None,
        settings: EmbeddingSettings | None = None,
    ):
        self.settings = settings or get_embedding_settings()

        if provider is not None:
            self.provider = provider

        elif self.settings.provider == "gemini":
            self.provider = GeminiEmbeddingProvider(
                self.settings
            )

        else:
            raise ValueError(
                "Unsupported embedding provider."
            )

    def _build_request(
        self,
        text: str,
        task: EmbeddingTask,
    ) -> EmbeddingRequest:

        if not isinstance(text, str):
            raise TypeError("Text must be a string.")

        if len(text) > self.settings.max_input_characters:
            raise EmbeddingInputTooLargeError(
                "Input exceeds configured character limit."
            )

        return EmbeddingRequest(
            text=text,
            task=task,
        )

    async def embed_document(
        self,
        text: str
    ) -> EmbeddingResult:

        request = self._build_request(
            text,
            EmbeddingTask.DOCUMENT,
        )

        return await self.provider.embed(request)

    async def embed_query(
        self,
        text: str
    ) -> EmbeddingResult:

        request = self._build_request(
            text,
            EmbeddingTask.QUERY,
        )

        return await self.provider.embed(request)

    async def embed_documents(
        self,
        texts: list[str]
    ) -> list[EmbeddingResult]:

        if not isinstance(texts, list):
            raise TypeError("Texts must be provided as a list.")

        if not texts:
            raise ValueError("Document batch cannot be empty.")

        requests = [
            self._build_request(
                text,
                EmbeddingTask.DOCUMENT,
            )
            for text in texts
        ]

        semaphore = asyncio.Semaphore(
            self.settings.max_concurrent_requests
        )

        async def process(request):
            async with semaphore:
                return await self.provider.embed(request)

        return await asyncio.gather(
            *(process(request) for request in requests)
        )

    async def close(self) -> None:
        await self.provider.close()