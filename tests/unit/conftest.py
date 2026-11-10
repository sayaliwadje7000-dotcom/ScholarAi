import pytest

from tests.support.factories import (
    EvaluationReportFactory,
    EvaluationResultFactory,
)
from app.evaluation.finalization.schemas import (
    FinalEvaluationStatus,
)


@pytest.fixture
def passed_evaluation_result():
    return EvaluationResultFactory.passed(
        check_name="unit_test_evaluation",
        metrics={"quality_score": 0.95},
    )


@pytest.fixture
def failed_evaluation_result():
    return EvaluationResultFactory.failed(
        check_name="failed_unit_test",
    )


@pytest.fixture
def partial_evaluation_result():
    return EvaluationResultFactory.partial(
        check_name="partial_unit_test",
    )


@pytest.fixture
def successful_evaluation_report():
    return EvaluationReportFactory.successful(count=3)


@pytest.fixture
def empty_evaluation_report():
    return EvaluationReportFactory.create(
        results=[],
        status=FinalEvaluationStatus.NOT_RUN,
    )


@pytest.fixture
def deterministic_evaluation_metrics():
    return {
        "precision": 0.91,
        "recall": 0.88,
        "f1_score": 0.895,
    }
