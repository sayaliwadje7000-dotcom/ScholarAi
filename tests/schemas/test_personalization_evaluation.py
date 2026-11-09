import uuid

import pytest
from pydantic import ValidationError

from app.schemas.personalization_evaluation import (
    EvaluationFeedback,
    EvaluationSegment,
    PersonalizationEvaluationCase,
    PersonalizationEvaluationRequest,
)


def test_valid_evaluation_case():
    case = PersonalizationEvaluationCase(
        case_id="evaluation-1",
        user_id=uuid.uuid4(),
        recommended_resource_ids=["resource-1", "resource-2"],
        relevant_resource_ids={"resource-1"},
        confidence=0.85,
        segment=EvaluationSegment.SUFFICIENT_DATA,
        feedback={
            "resource-1": EvaluationFeedback.POSITIVE,
        },
    )

    assert case.confidence == 0.85

    assert len(case.recommended_resource_ids) == 2


def test_confidence_must_be_between_zero_and_one():
    with pytest.raises(ValidationError):
        PersonalizationEvaluationCase(
            case_id="evaluation-1",
            user_id=uuid.uuid4(),
            confidence=1.5,
            segment=EvaluationSegment.COLD_START,
        )


def test_recommended_resource_ids_must_be_unique():
    with pytest.raises(ValidationError):
        PersonalizationEvaluationCase(
            case_id="evaluation-1",
            user_id=uuid.uuid4(),
            recommended_resource_ids=["A", "A"],
            confidence=0.5,
            segment=EvaluationSegment.LIMITED_DATA,
        )


def test_k_values_must_be_unique():
    with pytest.raises(ValidationError):
        PersonalizationEvaluationRequest(
            cases=[
                PersonalizationEvaluationCase(
                    case_id="evaluation-1",
                    user_id=uuid.uuid4(),
                    confidence=0.5,
                    segment=EvaluationSegment.COLD_START,
                )
            ],
            k_values=[3, 3],
        )


def test_k_values_are_sorted():
    request = PersonalizationEvaluationRequest(
        cases=[
            PersonalizationEvaluationCase(
                case_id="evaluation-1",
                user_id=uuid.uuid4(),
                confidence=0.5,
                segment=EvaluationSegment.COLD_START,
            )
        ],
        k_values=[10, 3, 5],
    )

    assert request.k_values == [3, 5, 10]