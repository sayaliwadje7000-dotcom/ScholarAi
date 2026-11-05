from abc import ABC, abstractmethod

from app.schemas.embeddings import (
    EmbeddingRequest,
    EmbeddingResult,
)


class BaseEmbeddingProvider(ABC):

    @abstractmethod
    async def embed(
        self,
        request: EmbeddingRequest
    ) -> EmbeddingResult:
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        raise NotImplementedError