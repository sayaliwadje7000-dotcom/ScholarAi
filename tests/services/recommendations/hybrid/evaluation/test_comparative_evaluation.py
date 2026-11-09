from app.services.recommendations.hybrid.evaluation import (
    EvaluationQuery,
    RecommendationEvaluator,
    ComparativeRecommendationEvaluator,
)


def test_compares_all_recommendation_strategies():

    evaluator = RecommendationEvaluator(k=3)

    comparison = ComparativeRecommendationEvaluator(
        evaluator
    )

    queries = [
        EvaluationQuery(
            query_id="python_basics",
            relevance={
                "resource_1": 3,
                "resource_2": 2,
                "resource_3": 1,
                "resource_4": 0,
            },
            catalog_ids=frozenset(
                {
                    "resource_1",
                    "resource_2",
                    "resource_3",
                    "resource_4",
                }
            ),
        )
    ]

    rankings = {
        "RULE_BASED": [
            [
                "resource_1",
                "resource_3",
                "resource_4",
            ]
        ],

        "CONTENT_BASED": [
            [
                "resource_2",
                "resource_1",
                "resource_3",
            ]
        ],

        "MACHINE_LEARNING": [
            [
                "resource_3",
                "resource_2",
                "resource_1",
            ]
        ],

        "HYBRID": [
            [
                "resource_1",
                "resource_2",
                "resource_3",
            ]
        ],
    }

    report = comparison.compare(
        rankings_by_strategy=rankings,
        queries=queries,
        latency_by_strategy={
            "RULE_BASED": [10.0],
            "CONTENT_BASED": [15.0],
            "MACHINE_LEARNING": [25.0],
            "HYBRID": [35.0],
        },
    )

    assert len(report.results) == 4

    assert "HYBRID" in report.results

    assert report.best_strategy_by_ndcg == "HYBRID"

    assert report.best_strategy_by_precision in {
    "CONTENT_BASED",
    "MACHINE_LEARNING",
    "HYBRID",
}

    assert report.lowest_latency_strategy == "RULE_BASED"


def test_comparison_rejects_missing_rankings():

    evaluator = RecommendationEvaluator(k=3)

    comparison = ComparativeRecommendationEvaluator(
        evaluator
    )

    try:
        comparison.compare(
            rankings_by_strategy={},
            queries=[],
        )
    except Exception:
        pass
    else:
        raise AssertionError(
            "Expected evaluation error."
        )