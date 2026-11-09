import pytest

from app.schemas.query_classification import (
    AcademicTaskType,
    QueryIntent,
)

from app.schemas.query_rewriting import (
    RewriteStrategy,
)

from app.services.query_rewriting_service import (
    QueryRewritingService,
)


@pytest.fixture
def service():
    return QueryRewritingService()


def test_normalizes_query(service):
    result = service.rewrite(
        "  Explain    binary   search.  "
    )

    assert result.normalized_query == (
        "Explain binary search."
    )


def test_preserves_original_query(service):
    query = "  Explain    binary search.  "

    result = service.rewrite(query)

    assert result.original_query == query


def test_enriches_comparison_query(service):
    result = service.rewrite(
        "Compare stack and queue."
    )

    assert result.retrieval_query == (
        "Compare stack and queue. similarities differences"
    )

    assert result.strategy == RewriteStrategy.TASK_ENRICHED


def test_enriches_explanation_query(service):
    result = service.rewrite(
        "Explain operating systems."
    )

    assert "concepts working mechanism examples" in (
        result.retrieval_query
    )


def test_enriches_problem_solving_query(service):
    result = service.rewrite(
        "Solve this equation."
    )

    assert "step-by-step solution" in result.retrieval_query


def test_enriches_summarization_query(service):
    result = service.rewrite(
        "Summarize operating systems."
    )

    assert "key points summary" in result.retrieval_query


def test_resolves_explain_more_with_context(service):
    result = service.rewrite(
        query="Explain more.",
        conversation_context="binary search",
    )

    assert result.standalone_query == (
        "Explain binary search"
    )

    assert result.context_used is True

    assert result.strategy == RewriteStrategy.CONTEXT_RESOLVED


def test_resolves_another_example_with_context(service):
    result = service.rewrite(
        query="Give another example.",
        conversation_context="binary search",
    )

    assert result.standalone_query == (
        "Give another example of binary search"
    )


def test_resolves_simplification_with_context(service):
    result = service.rewrite(
        query="Simplify it.",
        conversation_context="binary search",
    )

    assert result.standalone_query == (
        "Explain binary search in simpler terms"
    )


def test_resolves_continue_with_context(service):
    result = service.rewrite(
        query="Continue.",
        conversation_context="binary search",
    )

    assert result.standalone_query == (
        "Continue explaining binary search"
    )


def test_resolves_short_follow_up_with_context(service):
    result = service.rewrite(
        query="Why?",
        conversation_context="binary search",
    )

    assert result.standalone_query == (
        "Answer the follow-up question 'Why?' about binary search"
    )


def test_does_not_resolve_follow_up_without_context(service):
    result = service.rewrite(
        query="Explain more."
    )

    assert result.standalone_query == "Explain more."

    assert result.context_used is False


def test_does_not_force_context_on_academic_query(service):
    result = service.rewrite(
        query="Explain operating systems.",
        conversation_context="binary search",
    )

    assert result.standalone_query == (
        "Explain operating systems."
    )

    assert result.context_used is False


def test_preserves_document_grounded_query(service):
    result = service.rewrite(
        query="Explain this from my PDF."
    )

    assert result.standalone_query == (
        "Explain this from my PDF."
    )

    assert result.strategy == RewriteStrategy.UNCHANGED


def test_generates_deduplicated_search_queries(service):
    result = service.rewrite(
        "Compare stack and queue."
    )

    assert len(result.search_queries) == len(
        {
            query.lower()
            for query in result.search_queries
        }
    )

    assert len(result.search_queries) <= 3


def test_search_queries_include_standalone_query(service):
    result = service.rewrite(
        "Explain binary search."
    )

    assert result.standalone_query in result.search_queries


def test_rewritten_flag_is_true_when_query_changes(service):
    result = service.rewrite(
        "Compare stack and queue."
    )

    assert result.rewritten is True


def test_rewritten_flag_is_false_for_unchanged_unknown_query(service):
    result = service.rewrite(
        "Hello."
    )

    assert result.rewritten is False


def test_reuses_supplied_classification(service):
    classification = service.classifier.classify(
        "Compare stack and queue."
    )

    result = service.rewrite(
        query="Compare stack and queue.",
        classification=classification,
    )

    assert result.retrieval_query.endswith(
        "similarities differences"
    )


def test_rejects_non_string_query(service):
    with pytest.raises(ValueError):
        service.rewrite(None)


def test_rejects_empty_query(service):
    with pytest.raises(ValueError):
        service.rewrite("   ")


def test_rejects_oversized_query(service):
    with pytest.raises(ValueError):
        service.rewrite("x" * 5001)


def test_rejects_oversized_conversation_context(service):
    with pytest.raises(ValueError):
        service.rewrite(
            query="Explain more.",
            conversation_context="x" * 3001,
        )