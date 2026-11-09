import pytest

from pydantic import ValidationError

from app.schemas.query_classification import (
    AcademicTaskType,
    ClassificationEvidence,
    QueryClassification,
    QueryIntent,
)


def test_valid_query_classification():

    result = QueryClassification(
        intent=QueryIntent.ACADEMIC_LEARNING,
        task_type=AcademicTaskType.EXPLANATION,
        confidence=0.85,
        suggested_workflow="academic_response",
    )

    assert result.intent == QueryIntent.ACADEMIC_LEARNING
    assert result.task_type == AcademicTaskType.EXPLANATION
    assert result.confidence == 0.85


def test_classification_default_values():

    result = QueryClassification(
        intent=QueryIntent.UNKNOWN,
        task_type=AcademicTaskType.GENERAL,
        confidence=0.25,
        suggested_workflow="general_chat_fallback",
    )

    assert result.requires_conversation_context is False
    assert result.requires_document_context is False
    assert result.requires_external_resources is False
    assert result.requires_personalization is False
    assert result.ambiguous is False
    assert result.classifier_version == "1.0.0"


@pytest.mark.parametrize(
    "confidence",
    [-0.1, 1.1, 2.0],
)
def test_rejects_invalid_confidence(confidence):

    with pytest.raises(ValidationError):

        QueryClassification(
            intent=QueryIntent.UNKNOWN,
            task_type=AcademicTaskType.GENERAL,
            confidence=confidence,
            suggested_workflow="general_chat_fallback",
        )


def test_rejects_empty_workflow():

    with pytest.raises(ValidationError):

        QueryClassification(
            intent=QueryIntent.UNKNOWN,
            task_type=AcademicTaskType.GENERAL,
            confidence=0.25,
            suggested_workflow="",
        )


def test_classification_evidence_defaults():

    evidence = ClassificationEvidence()

    assert evidence.matched_patterns == []
    assert evidence.matched_keywords == []
    assert evidence.rules_applied == []


def test_classification_evidence_accepts_matches():

    evidence = ClassificationEvidence(
        matched_patterns=[r"\bcompare\b"],
        matched_keywords=["compare"],
        rules_applied=["selected_intent:academic_learning"],
    )

    assert len(evidence.matched_patterns) == 1
    assert len(evidence.matched_keywords) == 1
    assert len(evidence.rules_applied) == 1