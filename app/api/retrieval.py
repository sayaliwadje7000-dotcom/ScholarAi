from collections.abc import AsyncGenerator

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user

from app.database.session import get_db

from app.models.user import User

from app.schemas.retrieval import (
    RetrievalRequest,
    RetrievalResponse,
    RetrievedChunkResponse,
)

from app.services.embeddings.embedding_service import (
    EmbeddingService,
)

from app.services.retrieval_service import (
    RetrievalService,
    DocumentAccessDeniedError,
)


router = APIRouter()


async def get_embedding_service() -> AsyncGenerator[
    EmbeddingService,
    None,
]:
    """Provide an embedding service and close its client afterward."""

    service = EmbeddingService()

    try:
        yield service

    finally:
        await service.close()


@router.post(
    "/search",
    response_model=RetrievalResponse,
    summary="Search academic documents semantically",
)
async def semantic_retrieval(
    request: RetrievalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    embedding_service: EmbeddingService = Depends(
        get_embedding_service
    ),
):
    """
    Retrieve semantically relevant chunks from documents
    belonging exclusively to the authenticated user.
    """

    try:

        retrieval_service = RetrievalService(
            embedding_service=embedding_service,
        )

        results = await retrieval_service.search(
            db=db,
            user_id=current_user.id,
            request=request,
        )

        return RetrievalResponse(
            query=request.query,
            total_results=len(results),
            results=[
                RetrievedChunkResponse(
                    chunk_id=result.chunk_id,
                    document_id=result.document_id,
                    chunk_index=result.chunk_index,
                    text=result.text,
                    page_numbers=result.page_numbers,
                    start_page=result.start_page,
                    end_page=result.end_page,
                    similarity=result.similarity,
                    distance=result.distance,
                    provider=result.provider,
                    model=result.model,
                    dimensions=result.dimensions,
                    pipeline_version=result.pipeline_version,
                    chunking_version=result.chunking_version,
                )
                for result in results
            ],
        )

    except DocumentAccessDeniedError as exc:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        ) from exc