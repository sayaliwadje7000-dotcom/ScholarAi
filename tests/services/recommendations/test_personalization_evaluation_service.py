import uuid

import pytest

from app.schemas.personalization_evaluation import (
    EvaluationFeedback,
    EvaluationSegment,
    PersonalizationEvaluationCase,
    PersonalizationEvaluationRequest,
)

from app.services.recommendations.personalization_evaluation_service import (
    PersonalizationEvaluationService,
)


def make_case(
    case_id="case-1",
    recommended=None,
    relevant=None,
    confidence=0.8,
    segment=EvaluationSegment.SUFFICIENT_DATA,
    feedback=None,
    baseline=None,
):
    return PersonalizationEvaluationCase(
        case_id=case_id,
        user_id=uuid.uuid4(),
        recommended_resource_ids=(
            recommended or []
        ),
        relevant_resource_ids=set(
            relevant or []
        ),
        confidence=confidence,
        segment=segment,
        feedback=feedback or {},
        baseline_resource_ids=baseline or [],
    )


def test_precision_at_k():
    result = (
        PersonalizationEvaluationService
        ._precision_at_k(
            recommended=["A", "B", "C", "D"],
            relevant={"A", "C"},
            k=3,
        )
    )

    assert result == pytest.approx(2 / 3)


def test_recall_at_k():
    result = (
        PersonalizationEvaluationService
        ._recall_at_k(
            recommended=["A", "B", "C"],
            relevant={"A", "C", "D"},
            k=2,
        )
    )

    assert result == pytest.approx(1 / 3)


def test_ndcg_at_k_perfect_ranking():
    result = (
        PersonalizationEvaluationService
        ._ndcg_at_k(
            recommended=["A", "B", "C"],
            relevant={"A", "B"},
            k=3,
        )
    )

    assert result == pytest.approx(1.0)


def test_ndcg_at_k_reversed_ranking():
    result = (
        PersonalizationEvaluationService
        ._ndcg_at_k(
            recommended=["C", "B", "A"],
            relevant={"A", "B"},
            k=3,
        )
    )

    assert 0.0 < result < 1.0


def test_reciprocal_rank():
    result = (
        PersonalizationEvaluationService
        ._reciprocal_rank(
            recommended=["A", "B", "C"],
            relevant={"C"},
        )
    )

    assert result == pytest.approx(1 / 3)


def test_reciprocal_rank_without_relevant_item():
    result = (
        PersonalizationEvaluationService
        ._reciprocal_rank(
            recommended=["A", "B"],
            relevant={"C"},
        )
    )

    assert result == 0.0


def test_feedback_metrics():
    cases = [
        make_case(
            feedback={
                "A": EvaluationFeedback.POSITIVE,
                "B": EvaluationFeedback.NEGATIVE,
                "C": EvaluationFeedback.NEUTRAL,
            }
        )
    ]

    result = (
        PersonalizationEvaluationService
        ._calculate_feedback_metrics(cases)
    )

    assert result.total_feedback == 3
    assert result.positive_feedback == 1
    assert result.negative_feedback == 1
    assert result.neutral_feedback == 1

    assert result.positive_feedback_rate == pytest.approx(
        0.5
    )


def test_calibration_metrics():
    cases = [
        make_case(
            case_id="one",
            recommended=["A"],
            relevant={"A"},
            confidence=1.0,
        ),
        make_case(
            case_id="two",
            recommended=["B"],
            relevant={"A"},
            confidence=0.0,
        ),
    ]

    result = (
        PersonalizationEvaluationService
        ._calculate_calibration(
            cases,
            bins=10,
        )
    )

    assert result.brier_score == pytest.approx(0.0)
    assert result.expected_calibration_error == pytest.approx(
        0.0
    )
    assert result.evaluated_cases == 2


def test_baseline_comparison():
    cases = [
        make_case(
            recommended=["A", "B", "C"],
            relevant=["A", "B"],
            baseline=["C", "B", "A"],
        )
    ]

    result = (
        PersonalizationEvaluationService
        ._calculate_baseline_comparison(cases)
    )

    assert result is not None

    assert result.personalized_ndcg > result.baseline_ndcg

    assert result.ndcg_improvement > 0


def test_baseline_comparison_unavailable():
    cases = [
        make_case(
            recommended=["A"],
            relevant=["A"],
        )
    ]

    result = (
        PersonalizationEvaluationService
        ._calculate_baseline_comparison(cases)
    )

    assert result is None


def test_segment_metrics():
    cases = [
        make_case(
            case_id="one",
            recommended=["A"],
            relevant=["A"],
            segment=EvaluationSegment.SUFFICIENT_DATA,
        ),
        make_case(
            case_id="two",
            recommended=["B"],
            relevant=["A"],
            segment=EvaluationSegment.COLD_START,
        ),
    ]

    result = (
        PersonalizationEvaluationService
        ._calculate_segment_metrics(cases)
    )

    assert len(result) == 2

    assert all(
        item.evaluated_cases == 1
        for item in result
    )


def test_full_evaluation():
    cases = [
        make_case(
            case_id="one",
            recommended=["A", "B", "C"],
            relevant=["A", "B"],
            confidence=0.9,
            feedback={
                "A": EvaluationFeedback.POSITIVE,
                "B": EvaluationFeedback.POSITIVE,
            },
            baseline=["C", "B", "A"],
        ),
        make_case(
            case_id="two",
            recommended=["D", "E"],
            relevant=["D"],
            confidence=0.8,
            segment=EvaluationSegment.LIMITED_DATA,
            feedback={
                "D": EvaluationFeedback.NEGATIVE,
            },
            baseline=["E", "D"],
        ),
    ]

    request = PersonalizationEvaluationRequest(
        cases=cases,
        k_values=[3, 5],
        calibration_bins=10,
    )

    result = (
        PersonalizationEvaluationService.evaluate(
            request
        )
    )

    assert result.total_cases == 2

    assert result.cases_with_recommendations == 2

    assert result.recommendation_coverage == 1.0

    assert "@3" in result.ranking_metrics

    assert "@5" in result.ranking_metrics

    assert result.feedback.total_feedback == 3

    assert result.baseline_comparison is not None

    assert len(result.segment_evaluations) == 2


def test_evaluation_handles_empty_recommendation_lists():
    cases = [
        make_case(
            recommended=[],
            relevant=["A"],
        )
    ]

    request = PersonalizationEvaluationRequest(
        cases=cases,
        k_values=[3],
    )

    result = (
        PersonalizationEvaluationService.evaluate(
            request
        )
    )

    assert result.cases_with_recommendations == 0

    assert result.recommendation_coverage == 0.0

    assert any(
        "No recommendations" in warning
        for warning in result.evaluation_warnings
    )


def test_evaluation_warns_when_ground_truth_is_missing():
    cases = [
        make_case(
            recommended=["A", "B"],
            relevant=[],
        )
    ]

    request = PersonalizationEvaluationRequest(
        cases=cases,
    )

    result = (
        PersonalizationEvaluationService.evaluate(
            request
        )
    )

    assert any(
        "No ground-truth" in warning
        for warning in result.evaluation_warnings
    )


def test_duplicate_resource_ids_are_rejected():
    with pytest.raises(ValueError):
        make_case(
            recommended=["A", "A"],
            relevant=["A"],
        )


def test_invalid_k_values_are_rejected():
    with pytest.raises(ValueError):
        PersonalizationEvaluationRequest(
            cases=[
                make_case(
                    recommended=["A"],
                    relevant=["A"],
                )
            ],
            k_values=[0, 5],
        )


def test_empty_evaluation_request_is_rejected():
    with pytest.raises(ValueError):
        PersonalizationEvaluationRequest(
            cases=[],
        )