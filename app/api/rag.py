"""
ScholarAI RAG API.
"""

import logging

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.rag_dependencies import get_rag_service

from app.database.session import get_db

from app.models.user import User

from app.schemas.retrieval import RetrievalRequest
from app.schemas.rag import RAGAskResponse

from app.services.rag.rag_service import RAGService

from app.services.llm_providers.exceptions import (
    LLMProviderError,
)


logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/ask",
    response_model=RAGAskResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a question using uploaded documents",
    description=(
        "Retrieves relevant document chunks, generates an "
        "evidence-grounded answer, extracts citations, and "
        "returns grounding verification metadata."
    ),
)
async def ask_rag(
    request: RetrievalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service),
) -> RAGAskResponse:
    """
    Execute the integrated RAG pipeline for an authenticated user.
    """

    try:
        result = await rag_service.ask(
            db=db,
            user_id=current_user.id,
            request=request,
        )

        return RAGAskResponse.model_validate(result)

    except HTTPException:
        raise

    except LLMProviderError as exc:

        logger.exception(
            "LLM provider failure during RAG generation."
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The document question-answering service "
                "is temporarily unavailable."
            ),
        ) from exc

    except RuntimeError as exc:

        logger.exception(
            "RAG generation failed for user %s.",
            current_user.id,
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The RAG service is temporarily unavailable.",
        ) from exc