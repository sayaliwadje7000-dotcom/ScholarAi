from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document

from app.services.embeddings.embedding_service import (
    EmbeddingService,
)

from app.services.embeddings.semantic_search import (
    SemanticSearchService,
    SemanticSearchResult,
)

from app.schemas.retrieval import (
    RetrievalRequest,
)


class RetrievalError(Exception):
    """Base retrieval exception."""


class DocumentAccessDeniedError(RetrievalError):
    """Raised when requested documents are not owned by the user."""


class RetrievalService:
    """
    Coordinates query embedding and owner-scoped semantic retrieval.

    Document ownership is resolved before semantic search.
    The semantic search service never receives unverified document IDs.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        semantic_search_service: SemanticSearchService | None = None,
    ):
        self.embedding_service = embedding_service

        self.semantic_search_service = (
            semantic_search_service or SemanticSearchService()
        )

    @staticmethod
    def _get_owned_document_ids(
        db: Session,
        user_id: uuid.UUID,
        request: RetrievalRequest,
    ) -> list[uuid.UUID]:

        statement = select(Document.id).where(
            Document.user_id == user_id
        )

        if request.document_id is not None:
            statement = statement.where(
                Document.id == request.document_id
            )

        elif request.document_ids is not None:
            statement = statement.where(
                Document.id.in_(request.document_ids)
            )

        owned_ids = list(
            db.execute(statement).scalars().all()
        )

        if request.document_id is not None and not owned_ids:
            raise DocumentAccessDeniedError(
                "Document not found."
            )

        if request.document_ids is not None:

            if len(owned_ids) != len(request.document_ids):
                raise DocumentAccessDeniedError(
                    "One or more requested documents were not found."
                )

        return owned_ids

    async def search(
        self,
        db: Session,
        user_id: uuid.UUID,
        request: RetrievalRequest,
    ) -> list[SemanticSearchResult]:

        request.validate_document_filter()

        owned_document_ids = self._get_owned_document_ids(
            db=db,
            user_id=user_id,
            request=request,
        )

        if not owned_document_ids:
            return []

        query_embedding = await self.embedding_service.embed_query(
            request.query
        )

        results = self.semantic_search_service.search(
            db=db,
            query_vector=query_embedding.vector,
            document_ids=owned_document_ids,
            limit=request.limit,
            min_similarity=request.min_similarity,
        )

        return results