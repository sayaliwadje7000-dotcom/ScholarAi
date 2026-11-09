import pytest

from pydantic import ValidationError

from app.schemas.query_rewriting import (
    QueryRewriteRequest,
    QueryRewriteResult,
    RewriteStrategy,
)


def test_query_rewrite_request_accepts_valid_query():
    request = QueryRewriteRequest(
        query="Explain binary search."
    )

    assert request.query == "Explain binary search."
    assert request.conversation_context is None


def test_query_rewrite_request_strips_query():
    request = QueryRewriteRequest(
        query="  Explain binary search.  "
    )

    assert request.query == "Explain binary search."


def test_query_rewrite_request_rejects_empty_query():
    with pytest.raises(ValidationError):
        QueryRewriteRequest(query="   ")


def test_query_rewrite_request_rejects_oversized_query():
    with pytest.raises(ValidationError):
        QueryRewriteRequest(
            query="x" * 5001
        )


def test_query_rewrite_request_normalizes_empty_context():
    request = QueryRewriteRequest(
        query="Explain more.",
        conversation_context="   ",
    )

    assert request.conversation_context is None


def test_query_rewrite_result_validates_confidence_free_output():
    result = QueryRewriteResult(
        original_query="Explain more.",
        normalized_query="Explain more.",
        standalone_query="Explain binary search.",
        retrieval_query="Explain binary search concepts",
        search_queries=[
            "Explain binary search.",
            "Explain binary search concepts",
        ],
        strategy=RewriteStrategy.CONTEXT_RESOLVED,
        rewritten=True,
        context_used=True,
        reason="Resolved using conversation context.",
    )

    assert result.rewritten is True
    assert result.context_used is True


def test_query_rewrite_result_rejects_empty_search_query_list_item():
    with pytest.raises(ValidationError):
        QueryRewriteResult(
            original_query="Explain binary search.",
            normalized_query="Explain binary search.",
            standalone_query="Explain binary search.",
            retrieval_query="Explain binary search.",
            search_queries=[""],
            strategy=RewriteStrategy.UNCHANGED,
            rewritten=False,
            reason="No rewriting was necessary.",
        )