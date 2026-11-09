import pytest

from app.schemas.query_classification import (
    AcademicTaskType,
    QueryIntent,
)

from app.services.query_classification_service import (
    QueryClassificationService,
)


@pytest.fixture
def classifier():

    return QueryClassificationService()


# ---------------------------------------------------------
# NORMALIZATION
# ---------------------------------------------------------


def test_normalizes_query(classifier):

    result = classifier.normalize_query(
        "   Explain     Binary Search   "
    )

    assert result == "explain binary search"


def test_rejects_empty_query(classifier):

    with pytest.raises(ValueError):

        classifier.normalize_query("   ")


def test_rejects_non_string_query(classifier):

    with pytest.raises(ValueError):

        classifier.normalize_query(None)


def test_rejects_oversized_query(classifier):

    with pytest.raises(ValueError):

        classifier.normalize_query("a" * 5001)


# ---------------------------------------------------------
# PRIMARY INTENT CLASSIFICATION
# ---------------------------------------------------------


@pytest.mark.parametrize(
    "query, expected_intent",
    [
        (
            "Explain operating systems.",
            QueryIntent.ACADEMIC_LEARNING,
        ),
        (
            "Explain this topic from my PDF.",
            QueryIntent.DOCUMENT_GROUNDED,
        ),
        (
            "Find videos about Python programming.",
            QueryIntent.RESOURCE_DISCOVERY,
        ),
        (
            "Recommend me some books for DBMS.",
            QueryIntent.RECOMMENDATION,
        ),
        (
            "Generate MCQs on data structures.",
            QueryIntent.STUDY_MATERIAL_GENERATION,
        ),
        (
            "Explain something completely unrelated.",
            QueryIntent.ACADEMIC_LEARNING,
        ),
    ],
)
def test_classifies_primary_intents(
    classifier,
    query,
    expected_intent,
):

    result = classifier.classify(query)

    assert result.intent == expected_intent


def test_unknown_query_uses_fallback(classifier):

    result = classifier.classify(
        "asdf qwerty zxcv"
    )

    assert result.intent == QueryIntent.UNKNOWN
    assert result.suggested_workflow == "general_chat_fallback"


# ---------------------------------------------------------
# ACADEMIC TASK CLASSIFICATION
# ---------------------------------------------------------


@pytest.mark.parametrize(
    "query, expected_task",
    [
        (
            "Explain binary search.",
            AcademicTaskType.EXPLANATION,
        ),
        (
            "Compare stack and queue.",
            AcademicTaskType.COMPARISON,
        ),
        (
            "Solve this mathematical equation.",
            AcademicTaskType.PROBLEM_SOLVING,
        ),
        (
            "Summarize operating systems.",
            AcademicTaskType.SUMMARIZATION,
        ),
        (
            "Generate questions about DBMS.",
            AcademicTaskType.QUESTION_GENERATION,
        ),
        (
            "Define an algorithm.",
            AcademicTaskType.DEFINITION,
        ),
    ],
)
def test_detects_academic_task_type(
    classifier,
    query,
    expected_task,
):

    result = classifier.classify(query)

    assert result.task_type == expected_task


# ---------------------------------------------------------
# DOCUMENT CONTEXT
# ---------------------------------------------------------


def test_document_query_requires_document_context(classifier):

    result = classifier.classify(
        "Explain this topic from my PDF."
    )

    assert result.intent == QueryIntent.DOCUMENT_GROUNDED
    assert result.requires_document_context is True


def test_document_context_affects_summarization(classifier):

    result = classifier.classify(
        "Summarize the important points.",
        has_document_context=True,
    )

    assert result.task_type == AcademicTaskType.SUMMARIZATION
    assert result.requires_document_context is True


def test_document_context_alone_does_not_change_primary_intent(
    classifier,
):

    result = classifier.classify(
        "Explain binary search.",
        has_document_context=True,
    )

    assert result.intent == QueryIntent.ACADEMIC_LEARNING


# ---------------------------------------------------------
# CONVERSATION CONTEXT
# ---------------------------------------------------------


def test_follow_up_requires_existing_conversation(classifier):

    result = classifier.classify(
        "Explain more.",
        has_conversation_context=True,
    )

    assert result.intent == QueryIntent.CONVERSATION_FOLLOW_UP
    assert result.requires_conversation_context is True


def test_follow_up_without_conversation_is_not_assumed(
    classifier,
):

    result = classifier.classify(
        "Explain more."
    )

    assert result.intent != QueryIntent.CONVERSATION_FOLLOW_UP


def test_conversation_context_does_not_force_follow_up(
    classifier,
):

    result = classifier.classify(
        "Explain database normalization.",
        has_conversation_context=True,
    )

    assert result.intent == QueryIntent.ACADEMIC_LEARNING


# ---------------------------------------------------------
# WORKFLOW MAPPING
# ---------------------------------------------------------


@pytest.mark.parametrize(
    "query, expected_workflow",
    [
        (
            "Explain binary search.",
            "academic_response",
        ),
        (
            "Explain this from my PDF.",
            "document_rag",
        ),
        (
            "Find videos about machine learning.",
            "resource_discovery",
        ),
        (
            "Recommend me books about Python.",
            "recommendation",
        ),
        (
            "Generate MCQs on operating systems.",
            "study_material_generation",
        ),
        (
            "Explain more.",
            "conversation_aware_response",
        ),
    ],
)
def test_maps_intent_to_workflow(
    classifier,
    query,
    expected_workflow,
):

    result = classifier.classify(
        query,
        has_conversation_context=(
            query == "Explain more."
        ),
    )

    assert result.suggested_workflow == expected_workflow


# ---------------------------------------------------------
# CLASSIFICATION METADATA
# ---------------------------------------------------------


def test_classification_contains_evidence(classifier):

    result = classifier.classify(
        "Compare stack and queue."
    )

    assert result.evidence is not None
    assert result.evidence.matched_patterns
    assert result.evidence.rules_applied


def test_confidence_is_within_valid_range(classifier):

    result = classifier.classify(
        "Explain machine learning."
    )

    assert 0.0 <= result.confidence <= 1.0


def test_classifier_version_is_present(classifier):

    result = classifier.classify(
        "Explain machine learning."
    )

    assert result.classifier_version == "1.0.0"


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------


def test_rejects_invalid_minimum_confidence():

    with pytest.raises(ValueError):

        QueryClassificationService(
            minimum_confidence=1.5
        )


def test_accepts_custom_minimum_confidence():

    classifier = QueryClassificationService(
        minimum_confidence=0.60
    )

    assert classifier.minimum_confidence == 0.60