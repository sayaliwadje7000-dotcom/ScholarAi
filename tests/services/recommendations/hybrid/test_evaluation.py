from app.services.recommendations.hybrid.evaluation import (
    EvaluationQuery,
    RecommendationEvaluator,
    ComparativeRecommendationEvaluator,
)


def test_hybrid_outperforms_individual_components():

    evaluator = RecommendationEvaluator(k=3)

    comparison = ComparativeRecommendationEvaluator(
        evaluator
    )

    query = EvaluationQuery(
        query_id="data_structures",
        relevance={
            "bst": 3,
            "heap": 3,
            "graph": 2,
            "unrelated": 0,
        },
        catalog_ids=frozenset(
            {
                "bst",
                "heap",
                "graph",
                "unrelated",
            }
        ),
    )

    rankings = {
        "RULE_BASED": [
            ["bst", "unrelated", "graph"]
        ],

        "CONTENT_BASED": [
            ["graph", "unrelated", "heap"]
        ],

        "MACHINE_LEARNING": [
            ["unrelated", "graph", "bst"]
        ],

        "HYBRID": [
            ["bst", "heap", "graph"]
        ],
    }

    report = comparison.compare(
        rankings_by_strategy=rankings,
        queries=[query],
    )

    hybrid = report.results["HYBRID"]

    assert hybrid.precision_at_k == 1.0
    assert hybrid.recall_at_k == 1.0
    assert hybrid.ndcg_at_k == 1.0

    assert (
        hybrid.ndcg_at_k
        >
        report.results["RULE_BASED"].ndcg_at_k
    )

    assert (
        hybrid.ndcg_at_k
        >
        report.results["CONTENT_BASED"].ndcg_at_k
    )

    assert (
        hybrid.ndcg_at_k
        >
        report.results["MACHINE_LEARNING"].ndcg_at_k
    )