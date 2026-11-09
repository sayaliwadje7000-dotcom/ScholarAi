from __future__ import annotations

import logging
import uuid

from dataclasses import dataclass, field
from typing import Callable

from sqlalchemy.orm import Session

from app.schemas.retrieval import (
    RetrievalRequest,
    RetrievedChunkResponse,
)

from app.schemas.query_classification import (
    AcademicTaskType,
)

from app.schemas.response_intelligence import (
    ResponseFormat,
    ResponseIntelligenceRequest,
)

from app.services.retrieval_service import RetrievalService

from app.services.safety_service import (
    evaluate_message,
    validate_output,
)

from app.services.query_classification_service import (
    query_classification_service,
)

from app.services.query_rewriting_service import (
    query_rewriting_service,
)

from app.services.llm_providers.generation import (
    generate_with_provider_router,
)

from app.services.response_intelligence.response_intelligence_service import (
    response_intelligence_service,
)

from app.services.rag.context_builder import ContextBuilder

from app.services.rag.prompt_builder import RAGPromptBuilder

from app.services.rag.citation_service import (
    Citation,
    CitationIssue,
    CitationService,
)

from app.services.rag.grounding_service import (
    GroundingService,
    GroundingReport,
)


logger = logging.getLogger(__name__)


# ==========================================================
# RAG RESULT
# ==========================================================

@dataclass(frozen=True)
class RAGResult:

    query: str

    answer: str

    retrieved_chunks: list[RetrievedChunkResponse]

    total_retrieved: int

    grounded: bool

    included_chunks: int = 0

    excluded_chunks: int = 0

    context_characters: int = 0

    citations: list[Citation] = field(default_factory=list)

    citation_issues: list[CitationIssue] = field(default_factory=list)

    grounding_status: str = "not_verified"

    grounding_report: GroundingReport | None = None


# ==========================================================
# RAG SERVICE
# ==========================================================

class RAGService:

    def __init__(
        self,
        retrieval_service: RetrievalService,
        llm_generator: Callable | None = None,
        context_builder: ContextBuilder | None = None,
        prompt_builder: RAGPromptBuilder | None = None,
        citation_service: CitationService | None = None,
        grounding_service: GroundingService | None = None,
    ):

        self.retrieval_service = retrieval_service

        self.llm_generator = (
            llm_generator or generate_with_provider_router
        )

        self.context_builder = (
            context_builder or ContextBuilder()
        )

        self.prompt_builder = (
            prompt_builder or RAGPromptBuilder()
        )

        self.citation_service = (
            citation_service or CitationService()
        )

        self.grounding_service = (
            grounding_service
            or GroundingService(
                minimum_coverage=0.80,
                require_citations=True,
            )
        )

    # ======================================================
    # RETRIEVED CHUNK CONVERSION
    # ======================================================

    @staticmethod
    def _convert_retrieved_chunk(
        chunk,
    ) -> RetrievedChunkResponse:

        return RetrievedChunkResponse(
            chunk_id=str(chunk.chunk_id),
            document_id=chunk.document_id,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            page_numbers=chunk.page_numbers,
            start_page=chunk.start_page,
            end_page=chunk.end_page,
            similarity=chunk.similarity,
            distance=chunk.distance,
            provider=chunk.provider,
            model=chunk.model,
            dimensions=chunk.dimensions,
            pipeline_version=chunk.pipeline_version,
            chunking_version=chunk.chunking_version,
        )

    # ======================================================
    # RESPONSE FORMAT SELECTION
    # ======================================================

    @staticmethod
    def _select_response_format(
        task_type: AcademicTaskType,
    ) -> ResponseFormat:

        format_mapping = {
            AcademicTaskType.COMPARISON:
                ResponseFormat.COMPARISON,

            AcademicTaskType.PROBLEM_SOLVING:
                ResponseFormat.STEP_BY_STEP,

            AcademicTaskType.SUMMARIZATION:
                ResponseFormat.SUMMARY,
        }

        return format_mapping.get(
            task_type,
            ResponseFormat.PLAIN_TEXT,
        )

    # ======================================================
    # MAIN RAG WORKFLOW
    # ======================================================

    async def ask(
        self,
        db: Session,
        user_id: uuid.UUID,
        request: RetrievalRequest,
    ) -> RAGResult:

        original_query = request.query

        # --------------------------------------------------
        # STEP 1: INPUT SAFETY
        # --------------------------------------------------

        safety_result = evaluate_message(original_query)

        if not safety_result.allowed:

            return RAGResult(
                query=original_query,
                answer=(
                    safety_result.response
                    or "This request cannot be processed."
                ),
                retrieved_chunks=[],
                total_retrieved=0,
                grounded=False,
                grounding_status="not_verified",
            )

        # --------------------------------------------------
        # STEP 2: QUERY CLASSIFICATION
        # --------------------------------------------------

        classification = query_classification_service.classify(
            query=original_query,
            has_conversation_context=False,
            has_document_context=True,
        )

        logger.info(
            "RAG query classified",
            extra={
                "intent": classification.intent.value,
                "task_type": classification.task_type.value,
                "confidence": classification.confidence,
                "classifier_version": (
                    classification.classifier_version
                ),
            },
        )

        # --------------------------------------------------
        # STEP 3: QUERY REWRITING
        # --------------------------------------------------

        rewrite_result = query_rewriting_service.rewrite(
            query=original_query,
            classification=classification,
        )

        logger.info(
            "RAG query rewritten",
            extra={
                "strategy": rewrite_result.strategy.value,
                "rewritten": rewrite_result.rewritten,
                "classifier_version": (
                    rewrite_result.classifier_version
                ),
            },
        )

        # Use retrieval-specific enrichment only for retrieval.
        # Keep original_query for the final answer prompt.
        retrieval_request = request.model_copy(
            update={
                "query": rewrite_result.retrieval_query,
            }
        )

        # --------------------------------------------------
        # STEP 4: DOCUMENT RETRIEVAL
        # --------------------------------------------------

        retrieved_results = await self.retrieval_service.search(
            db=db,
            user_id=user_id,
            request=retrieval_request,
        )

        retrieved_chunks = [
            self._convert_retrieved_chunk(chunk)
            for chunk in retrieved_results
        ]

        # --------------------------------------------------
        # STEP 5: HANDLE EMPTY RETRIEVAL
        # --------------------------------------------------

        if not retrieved_chunks:

            return RAGResult(
                query=original_query,
                answer=(
                    "I could not find relevant information in the "
                    "selected documents. Please rephrase your question "
                    "or select another document."
                ),
                retrieved_chunks=[],
                total_retrieved=0,
                grounded=False,
                grounding_status="insufficient_evidence",
            )

        # --------------------------------------------------
        # STEP 6: BUILD CONTEXT
        # --------------------------------------------------

        context_result = self.context_builder.build(
            retrieved_chunks
        )

        if not context_result.context:

            return RAGResult(
                query=original_query,
                answer=(
                    "The retrieved document content could not fit "
                    "within the available context budget."
                ),
                retrieved_chunks=retrieved_chunks,
                total_retrieved=len(retrieved_chunks),
                grounded=False,
                included_chunks=0,
                excluded_chunks=len(retrieved_chunks),
                context_characters=0,
                grounding_status="insufficient_evidence",
            )

        # --------------------------------------------------
        # STEP 7: BUILD RAG PROMPT
        # --------------------------------------------------

        prompt_result = self.prompt_builder.build(
            query=original_query,
            context=context_result.context,
            sources=context_result.sources,
        )

        # --------------------------------------------------
        # STEP 8: GENERATE THROUGH PROVIDER ROUTER
        # --------------------------------------------------

        answer = await self.llm_generator(
            prompt_result.prompt
        )

        if not isinstance(answer, str) or not answer.strip():

            raise RuntimeError(
                "The LLM provider returned an invalid RAG response."
            )

        answer = answer.strip()

        # --------------------------------------------------
        # STEP 9: OUTPUT SAFETY
        # --------------------------------------------------

        output_safety = validate_output(answer)

        if not output_safety.allowed:

            return RAGResult(
                query=original_query,
                answer=(
                    output_safety.response
                    or "The generated response could not be displayed."
                ),
                retrieved_chunks=retrieved_chunks,
                total_retrieved=len(retrieved_chunks),
                grounded=False,
                included_chunks=context_result.included_chunks,
                excluded_chunks=context_result.excluded_chunks,
                context_characters=context_result.total_characters,
                grounding_status="not_verified",
            )

        # --------------------------------------------------
        # STEP 10: RESPONSE INTELLIGENCE
        # --------------------------------------------------

        response_format = self._select_response_format(
            classification.task_type
        )

        intelligence_result = (
            response_intelligence_service.process(
                ResponseIntelligenceRequest(
                    response=answer,
                    response_format=response_format,
                    validate_safety=False,
                )
            )
        )

        answer = intelligence_result.response

        logger.info(
            "RAG response intelligence completed",
            extra={
                "response_format": (
                    intelligence_result.response_format.value
                ),
                "validation_status": (
                    intelligence_result.validation_status.value
                ),
                "quality_issue_count": len(
                    intelligence_result.quality_issues
                ),
            },
        )

        # --------------------------------------------------
        # STEP 11: CITATION EXTRACTION
        # --------------------------------------------------

        citation_result = self.citation_service.extract(
            answer=answer,
            sources=context_result.sources,
        )

        # --------------------------------------------------
        # STEP 12: GROUNDING VERIFICATION
        # --------------------------------------------------

        grounding_report = self.grounding_service.verify(
            answer=answer,
            sources=context_result.sources,
            citation_result=citation_result,
        )

        # --------------------------------------------------
        # STEP 13: RETURN STRUCTURED RESULT
        # --------------------------------------------------

        return RAGResult(
            query=original_query,
            answer=answer,
            retrieved_chunks=retrieved_chunks,
            total_retrieved=len(retrieved_chunks),
            grounded=(
                grounding_report.status == "citation_checks_passed"
            ),
            included_chunks=context_result.included_chunks,
            excluded_chunks=context_result.excluded_chunks,
            context_characters=context_result.total_characters,
            citations=citation_result.citations,
            citation_issues=citation_result.issues,
            grounding_status=grounding_report.status,
            grounding_report=grounding_report,
        )