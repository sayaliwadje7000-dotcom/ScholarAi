from app.services.recommendations.evaluation_metrics import (
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
    ndcg_at_k,
)


def test_recommendation_quality_baseline():
    """
    Deterministic evaluation baseline.

    These are synthetic relevance labels, not real user behavior.
    """

    catalog = {
        "binary_tree_notes",
        "binary_tree_video",
        "graph_notes",
        "sorting_tutorial",
        "database_course",
    }

    relevant = {
        "binary_tree_notes",
        "binary_tree_video",
        "graph_notes",
    }

    recommended = [
        "binary_tree_notes",
        "sorting_tutorial",
        "binary_tree_video",
    ]

    assert set(recommended).issubset(catalog)

    precision = precision_at_k(
        recommended,
        relevant,
        3,
    )

    recall = recall_at_k(
        recommended,
        relevant,
        3,
    )

    mrr = reciprocal_rank(
        recommended,
        relevant,
    )

    ndcg = ndcg_at_k(
        recommended,
        relevant,
        3,
    )

    assert precision == 2 / 3
    assert recall == 2 / 3
    assert mrr == 1.0
    assert 0.0 <= ndcg <= 1.0