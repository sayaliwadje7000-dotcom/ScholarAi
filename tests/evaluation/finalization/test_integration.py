import json

from app.evaluation.finalization.registry import (
    FinalEvaluationRegistry,
)
from app.evaluation.finalization.runner import (
    FinalEvaluationRunner,
)
from app.evaluation.finalization.reporting import (
    FinalEvaluationReporter,
)
from app.evaluation.finalization.schemas import (
    FinalEvaluationStatus,
)


def test_complete_final_evaluation_workflow(tmp_path):
    registry = FinalEvaluationRegistry()

    def rag_evaluator():
        return {
            "status": "passed",
            "message": "RAG evaluation completed.",
            "metrics": {
                "precision_at_5": 0.91,
                "recall_at_5": 0.88,
            },
        }

    def recommendation_evaluator():
        return {
            "status": "passed",
            "message": "Recommendation evaluation completed.",
            "metrics": {
                "precision_at_5": 0.89,
            },
        }

    def optimization_evaluator():
        return {
            "status": "partial",
            "message": "Optimization completed with limitations.",
            "metrics": {
                "improvement": 0.12,
            },
        }

    registry.register("rag_quality", "rag", rag_evaluator)
    registry.register(
        "recommendation_quality",
        "recommendation",
        recommendation_evaluator,
    )
    registry.register(
        "optimization_validation",
        "optimization",
        optimization_evaluator,
    )

    runner = FinalEvaluationRunner(registry)

    report = runner.run(
        metadata={
            "project": "ScholarAI",
            "phase": "19.10",
        }
    )

    assert report.total_checks == 3
    assert report.passed_checks == 2
    assert report.partial_checks == 1
    assert report.status == FinalEvaluationStatus.PARTIAL

    json_path = tmp_path / "final-report.json"
    text_path = tmp_path / "final-report.txt"

    FinalEvaluationReporter.save_json(report, json_path)
    FinalEvaluationReporter.save_text(report, text_path)

    assert json_path.exists()
    assert text_path.exists()

    parsed = json.loads(
        json_path.read_text(encoding="utf-8")
    )

    assert parsed["metadata"]["project"] == "ScholarAI"
    assert parsed["total_checks"] == 3
