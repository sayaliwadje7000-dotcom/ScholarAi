import pytest

from app.services.recommendations.hybrid.evaluation import (
    EvaluationQuery,
    RecommendationEvaluator,
    HybridWeightExperimentRunner,
    WeightExperimentError,
)


def test_weight_experiment_runs_successfully():

    evaluator = RecommendationEvaluator(k=3)

    runner = HybridWeightExperimentRunner(
        evaluator
    )

    queries = [
        EvaluationQuery(
            query_id="python",
            relevance={
                "resource_1": 3,
                "resource_2": 2,
                "resource_3": 1,
            },
        )
    ]

    weights = {
        "RULE_BASED": 0.30,
        "CONTENT_BASED": 0.30,
        "MACHINE_LEARNING": 0.40,
    }

    def ranking_function(weights, query):
        return [
            "resource_1",
            "resource_2",
            "resource_3",
        ]

    result = runner.run_experiment(
        weights=weights,
        queries=queries,
        ranking_function=ranking_function,
    )

    assert result.ndcg_at_k == pytest.approx(1.0)

    assert result.precision_at_k == pytest.approx(1.0)

    assert result.recall_at_k == pytest.approx(1.0)


def test_weight_experiment_rejects_invalid_total():

    evaluator = RecommendationEvaluator()

    runner = HybridWeightExperimentRunner(
        evaluator
    )

    invalid_weights = {
        "RULE_BASED": 0.30,
        "CONTENT_BASED": 0.30,
        "MACHINE_LEARNING": 0.60,
    }

    with pytest.raises(WeightExperimentError):

        runner.validate_weights(
            invalid_weights
        )


def test_grid_search_ranks_weight_configurations():

    evaluator = RecommendationEvaluator(k=3)

    runner = HybridWeightExperimentRunner(
        evaluator
    )

    queries = [
        EvaluationQuery(
            query_id="python",
            relevance={
                "resource_1": 3,
                "resource_2": 2,
                "resource_3": 1,
            },
        )
    ]

    configurations = [
        {
            "RULE_BASED": 0.30,
            "CONTENT_BASED": 0.30,
            "MACHINE_LEARNING": 0.40,
        },
        {
            "RULE_BASED": 0.40,
            "CONTENT_BASED": 0.30,
            "MACHINE_LEARNING": 0.30,
        },
    ]

    def ranking_function(weights, query):

        if weights["RULE_BASED"] == 0.40:
            return [
                "resource_1",
                "resource_2",
                "resource_3",
            ]

        return [
            "resource_3",
            "resource_2",
            "resource_1",
        ]

    results = runner.grid_search(
        configurations=configurations,
        queries=queries,
        ranking_function=ranking_function,
    )

    assert len(results) == 2

    assert results[0].ndcg_at_k >= results[1].ndcg_at_k