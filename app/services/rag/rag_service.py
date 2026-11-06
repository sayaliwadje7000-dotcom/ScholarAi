from __future__ import annotations

import uuid

from dataclasses import dataclass, field
from typing import Callable

from sqlalchemy.orm import Session

from app.schemas.retrieval import (
    RetrievalRequest,
    RetrievedChunkResponse,
)

from app.services.retrieval_service import RetrievalService

from app.services.llm_service import generate_llm_response

from app.services.safety_service import (
    evaluate_message,
    validate_output,
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


class RAGService:

    def __init__(
        self,
        retrieval_service: RetrievalService,
        llm_generator: Callable = generate_llm_response,
        context_builder: ContextBuilder | None = None,
        prompt_builder: RAGPromptBuilder | None = None,
        citation_service: CitationService | None = None,
        grounding_service: GroundingService | None = None,
    ):

        self.retrieval_service = retrieval_service
        self.llm_generator = llm_generator

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
            grounding_service or GroundingService(
                minimum_coverage=0.80,
                require_citations=True,
            )
        )

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

    async def ask(
        self,
        db: Session,
        user_id: uuid.UUID,
        request: RetrievalRequest,
    ) -> RAGResult:

        # STEP 1: INPUT SAFETY SCREENING

        safety_result = evaluate_message(request.query)

        if not safety_result.allowed:

            return RAGResult(
                query=request.query,
                answer=(
                    safety_result.response
                    or "This request cannot be processed."
                ),
                retrieved_chunks=[],
                total_retrieved=0,
                grounded=False,
                grounding_status="not_verified",
            )

        # STEP 2: DOCUMENT RETRIEVAL

        retrieved_results = await self.retrieval_service.search(
            db=db,
            user_id=user_id,
            request=request,
        )

        retrieved_chunks = [
            self._convert_retrieved_chunk(chunk)
            for chunk in retrieved_results
        ]

        # STEP 3: HANDLE EMPTY RETRIEVAL

        if not retrieved_chunks:

            return RAGResult(
                query=request.query,
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

        # STEP 4: BUILD CONTEXT

        context_result = self.context_builder.build(
            retrieved_chunks
        )

        if not context_result.context:

            return RAGResult(
                query=request.query,
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

        # STEP 5: BUILD RAG PROMPT

        prompt_result = self.prompt_builder.build(
            query=request.query,
            context=context_result.context,
            sources=context_result.sources,
        )

        # STEP 6: GENERATE ANSWER

        answer = await self.llm_generator(
            prompt_result.prompt
        )

        # STEP 7: OUTPUT SAFETY VALIDATION

        output_safety = validate_output(answer)

        if not output_safety.allowed:

            return RAGResult(
                query=request.query,
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

        # STEP 8: CITATION EXTRACTION AND VALIDATION

        citation_result = self.citation_service.extract(
            answer=answer,
            sources=context_result.sources,
        )

        # STEP 9: GROUNDING AND CITATION COVERAGE VERIFICATION

        grounding_report = self.grounding_service.verify(
            answer=answer,
            sources=context_result.sources,
            citation_result=citation_result,
        )

        # STEP 10: RETURN STRUCTURED RAG RESULT

        return RAGResult(
            query=request.query,
            answer=answer,
            retrieved_chunks=retrieved_chunks,
            total_retrieved=len(retrieved_chunks),

            # This indicates citation checks passed.
            # It does not prove semantic faithfulness.
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