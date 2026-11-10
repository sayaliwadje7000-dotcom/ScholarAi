import asyncio

import pytest

from app.evaluation.rag.adapters import CallableRAGAdapter
from app.schemas.rag_evaluation import RAGEvaluationCase


def create_case():
    return RAGEvaluationCase(
        case_id="case-1",
        query="Explain RAG",
    )


def test_sync_pipeline_adapter():
    adapter = CallableRAGAdapter(
        lambda case: {"answer": "RAG answer"}
    )

    result = asyncio.run(
        adapter.run(create_case())
    )

    assert result["answer"] == "RAG answer"


def test_async_pipeline_adapter():
    async def pipeline(case):
        return {"answer": "Async RAG answer"}

    adapter = CallableRAGAdapter(pipeline)

    result = asyncio.run(
        adapter.run(create_case())
    )

    assert result["answer"] == "Async RAG answer"


def test_sync_pipeline_returning_awaitable():
    async def result():
        return {"answer": "Awaitable result"}

    adapter = CallableRAGAdapter(
        lambda case: result()
    )

    output = asyncio.run(
        adapter.run(create_case())
    )

    assert output["answer"] == "Awaitable result"


def test_non_callable_rejected():
    with pytest.raises(TypeError):
        CallableRAGAdapter(None)
