from __future__ import annotations

import asyncio
import uuid

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import app.services.rag.rag_service as rag_module

from app.schemas.retrieval import RetrievalRequest
from app.services.rag.rag_service import RAGService


# ============================================================
# TEST FIXTURES
# ============================================================

USER_ID = uuid.uuid4()
DOCUMENT_ID = uuid.uuid4()


def create_chunk(
    chunk_id="chunk-001",
    text="Machine learning is a branch of artificial intelligence.",
):
    return SimpleNamespace(
        chunk_id=chunk_id,
        document_id=DOCUMENT_ID,
        chunk_index=0,
        text=text,
        page_numbers=[1],
        start_page=1,
        end_page=1,
        similarity=0.95,
        distance=0.05,
        provider="gemini",
        model="gemini-embedding-2",
        dimensions=1536,
        pipeline_version="1.0",
        chunking_version="1.0",
    )


def create_context(
    context="Machine learning is a branch of artificial intelligence.",
):
    return SimpleNamespace(
        context=context,
        sources=[
            SimpleNamespace(
                source_id="S1",
                chunk_id="chunk-001",
            )
        ] if context else [],
        included_chunks=1 if context else 0,
        excluded_chunks=0,
        total_characters=len(context),
    )


def create_prompt():
    return SimpleNamespace(
        prompt="Answer using only the supplied evidence."
    )


def create_citation_result():
    return SimpleNamespace(
        citations=[],
        issues=[],
    )


def create_grounding_report():
    return SimpleNamespace(
        status="citation_checks_passed",
    )


class FakeContextBuilder:

    def __init__(self, context=None):
        self.context = context or create_context()

    def build(self, chunks):
        return self.context


class FakePromptBuilder:

    def build(self, query, context, sources):
        return create_prompt()


class FakeCitationService:

    def extract(self, answer, sources):
        return create_citation_result()


class FakeGroundingService:

    def verify(self, answer, sources, citation_result):
        return create_grounding_report()


class FakeRetrievalService:

    def __init__(self, chunks=None):
        self.chunks = (
            [create_chunk()]
            if chunks is None
            else chunks
        )

        self.search = AsyncMock(
            return_value=self.chunks
        )


def create_service(
    retrieval_service=None,
    llm_generator=None,
    context_builder=None,
):

    return RAGService(
        retrieval_service=(
            retrieval_service or FakeRetrievalService()
        ),
        llm_generator=(
            llm_generator or AsyncMock(
                return_value=(
                    "Machine learning is a branch "
                    "of artificial intelligence. [S1]"
                )
            )
        ),
        context_builder=(
            context_builder or FakeContextBuilder()
        ),
        prompt_builder=FakePromptBuilder(),
        citation_service=FakeCitationService(),
        grounding_service=FakeGroundingService(),
    )


@pytest.fixture(autouse=True)
def allow_test_safety_checks(monkeypatch):

    monkeypatch.setattr(
        rag_module,
        "evaluate_message",
        lambda message: SimpleNamespace(
            allowed=True,
            response=None,
        ),
    )

    monkeypatch.setattr(
        rag_module,
        "validate_output",
        lambda answer: SimpleNamespace(
            allowed=True,
            response=None,
        ),
    )


# ============================================================
# 1. COMPLETE RAG WORKFLOW
# ============================================================

@pytest.mark.asyncio
async def test_complete_rag_workflow():

    retrieval = FakeRetrievalService()

    llm = AsyncMock(
        return_value=(
            "Machine learning is a branch "
            "of artificial intelligence. [S1]"
        )
    )

    service = create_service(
        retrieval_service=retrieval,
        llm_generator=llm,
    )

    request = RetrievalRequest(
        query="What is machine learning?",
        limit=5,
    )

    result = await service.ask(
        db=object(),
        user_id=USER_ID,
        request=request,
    )

    assert result.query == request.query

    assert result.total_retrieved == 1

    assert result.included_chunks == 1

    assert result.grounding_status == (
        "citation_checks_passed"
    )

    assert result.grounded is True

    retrieval.search.assert_awaited_once()

    llm.assert_awaited_once()


# ============================================================
# 2. USER ID PROPAGATION
# ============================================================

@pytest.mark.asyncio
async def test_retrieval_receives_authenticated_user_id():

    retrieval = FakeRetrievalService()

    service = create_service(
        retrieval_service=retrieval
    )

    await service.ask(
        db=object(),
        user_id=USER_ID,
        request=RetrievalRequest(
            query="Explain neural networks",
            limit=5,
        ),
    )

    retrieval.search.assert_awaited_once()

    call_arguments = (
        retrieval.search.await_args.kwargs
    )

    assert call_arguments["user_id"] == USER_ID


# ============================================================
# 3. EMPTY RETRIEVAL
# ============================================================

@pytest.mark.asyncio
async def test_empty_retrieval_returns_insufficient_evidence():

    retrieval = FakeRetrievalService(
        chunks=[]
    )

    llm = AsyncMock()

    service = create_service(
        retrieval_service=retrieval,
        llm_generator=llm,
    )

    result = await service.ask(
        db=object(),
        user_id=USER_ID,
        request=RetrievalRequest(
            query="Explain an unavailable topic",
            limit=5,
        ),
    )

    assert result.total_retrieved == 0

    assert result.grounded is False

    assert result.grounding_status == (
        "insufficient_evidence"
    )

    llm.assert_not_awaited()


# ============================================================
# 4. EMPTY CONTEXT
# ============================================================

@pytest.mark.asyncio
async def test_empty_context_prevents_llm_generation():

    retrieval = FakeRetrievalService()

    llm = AsyncMock()

    context_builder = FakeContextBuilder(
        context=create_context("")
    )

    service = create_service(
        retrieval_service=retrieval,
        llm_generator=llm,
        context_builder=context_builder,
    )

    result = await service.ask(
        db=object(),
        user_id=USER_ID,
        request=RetrievalRequest(
            query="Explain machine learning",
            limit=5,
        ),
    )

    assert result.grounded is False

    assert result.grounding_status == (
        "insufficient_evidence"
    )

    llm.assert_not_awaited()


# ============================================================
# 5. RETRIEVAL FAILURE
# ============================================================

@pytest.mark.asyncio
async def test_retrieval_failure_propagates():

    retrieval = FakeRetrievalService()

    retrieval.search.side_effect = RuntimeError(
        "Retrieval provider unavailable"
    )

    service = create_service(
        retrieval_service=retrieval
    )

    with pytest.raises(RuntimeError):
        await service.ask(
            db=object(),
            user_id=USER_ID,
            request=RetrievalRequest(
                query="Explain AI",
                limit=5,
            ),
        )


# ============================================================
# 6. LLM FAILURE
# ============================================================

@pytest.mark.asyncio
async def test_llm_failure_propagates():

    llm = AsyncMock(
        side_effect=RuntimeError(
            "LLM provider unavailable"
        )
    )

    service = create_service(
        llm_generator=llm
    )

    with pytest.raises(RuntimeError):
        await service.ask(
            db=object(),
            user_id=USER_ID,
            request=RetrievalRequest(
                query="Explain AI",
                limit=5,
            ),
        )


# ============================================================
# 7. OUTPUT SAFETY FAILURE
# ============================================================

@pytest.mark.asyncio
async def test_unsafe_output_is_not_returned(
    monkeypatch,
):

    monkeypatch.setattr(
        rag_module,
        "validate_output",
        lambda answer: SimpleNamespace(
            allowed=False,
            response="The generated response was blocked.",
        ),
    )

    service = create_service()

    result = await service.ask(
        db=object(),
        user_id=USER_ID,
        request=RetrievalRequest(
            query="Explain AI",
            limit=5,
        ),
    )

    assert result.answer == (
        "The generated response was blocked."
    )

    assert result.grounded is False

    assert result.grounding_status == (
        "not_verified"
    )


# ============================================================
# 8. INPUT SAFETY FAILURE
# ============================================================

@pytest.mark.asyncio
async def test_unsafe_input_prevents_retrieval(
    monkeypatch,
):

    monkeypatch.setattr(
        rag_module,
        "evaluate_message",
        lambda message: SimpleNamespace(
            allowed=False,
            response="Request rejected.",
        ),
    )

    retrieval = FakeRetrievalService()

    service = create_service(
        retrieval_service=retrieval
    )

    result = await service.ask(
        db=object(),
        user_id=USER_ID,
        request=RetrievalRequest(
            query="Unsafe request",
            limit=5,
        ),
    )

    assert result.answer == "Request rejected."

    retrieval.search.assert_not_awaited()


# ============================================================
# 9. CONCURRENT REQUEST ISOLATION
# ============================================================

@pytest.mark.asyncio
async def test_concurrent_requests_are_independent():

    retrieval = FakeRetrievalService()

    llm = AsyncMock(
        side_effect=[
            "Answer one. [S1]",
            "Answer two. [S1]",
        ]
    )

    service = create_service(
        retrieval_service=retrieval,
        llm_generator=llm,
    )

    request_one = RetrievalRequest(
        query="Question one",
        limit=5,
    )

    request_two = RetrievalRequest(
        query="Question two",
        limit=5,
    )

    result_one, result_two = await asyncio.gather(
        service.ask(
            db=object(),
            user_id=USER_ID,
            request=request_one,
        ),
        service.ask(
            db=object(),
            user_id=USER_ID,
            request=request_two,
        ),
    )

    assert result_one.query == "Question one"

    assert result_two.query == "Question two"

    assert result_one.answer != result_two.answer

    assert retrieval.search.await_count == 2

    assert llm.await_count == 2