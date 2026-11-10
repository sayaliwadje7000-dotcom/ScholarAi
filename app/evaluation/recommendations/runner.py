import asyncio
import time

from app.evaluation.recommendations.adapters import (
    CallableRecommendationAdapter,
)
from app.evaluation.recommendations.metrics import (
    precision_at_k,
    recall_at_k,
    hit_rate_at_k,
    reciprocal_rank,
    ndcg_at_k,
    personalization_alignment,
    discovery_relevance,
    intra_list_diversity,
    novelty,
    serendipity,
)
from app.evaluation.recommendations.schemas import (
    RecommendationEvaluationConfig,
    RecommendationCaseMetrics,
    RecommendationCaseResult,
    RecommendationEvaluationReport,
)


class RecommendationEvaluationRunner:
    def __init__(self, adapter, config=None):
        self.adapter = adapter
        self.config = config or RecommendationEvaluationConfig()

    async def _evaluate_case(self, case):
        started = time.perf_counter()

        recommendations = await asyncio.wait_for(
            self.adapter.recommend(case),
            timeout=self.config.timeout_seconds,
        )

        latency_ms = (time.perf_counter() - started) * 1000
        recommended_ids = [
            item["item_id"] for item in recommendations
        ]

        if len(recommended_ids) != len(set(recommended_ids)):
            raise ValueError(
                f"Duplicate recommendations in case {case.case_id}"
            )

        relevant = set(case.relevant_item_ids)
        expected = set(case.expected_item_ids)
        discovery = set(case.discovery_item_ids)

        item_tags = {
            **case.item_tags,
            **{
                item["item_id"]: item.get("tags", [])
                for item in recommendations
                if "tags" in item
            },
        }

        metrics = RecommendationCaseMetrics(
            precision_at_k=precision_at_k(
                recommended_ids, relevant, self.config.k
            ),
            recall_at_k=recall_at_k(
                recommended_ids, relevant, self.config.k
            ),
            hit_rate_at_k=hit_rate_at_k(
                recommended_ids, relevant, self.config.k
            ),
            reciprocal_rank=reciprocal_rank(
                recommended_ids, relevant
            ),
            ndcg_at_k=ndcg_at_k(
                recommended_ids, relevant, self.config.k
            ),
            personalization_alignment=personalization_alignment(
                recommended_ids,
                item_tags,
                set(case.user_preference_tags),
            ),
            discovery_relevance=discovery_relevance(
                recommended_ids, discovery, relevant
            ),
            intra_list_diversity=intra_list_diversity(
                recommended_ids, item_tags
            ),
            novelty=novelty(
                recommended_ids, case.item_popularity
            ),
            serendipity=serendipity(
                recommended_ids, expected, relevant
            ),
            latency_ms=latency_ms,
        )

        thresholds = {
            "precision_at_k": self.config.minimum_precision,
            "recall_at_k": self.config.minimum_recall,
            "ndcg_at_k": self.config.minimum_ndcg,
            "personalization_alignment": self.config.minimum_personalization,
            "discovery_relevance": self.config.minimum_discovery_relevance,
        }

        failed_checks = [
            name for name, threshold in thresholds.items()
            if getattr(metrics, name) < threshold
        ]

        return RecommendationCaseResult(
            case_id=case.case_id,
            user_id=case.user_id,
            metrics=metrics,
            passed=not failed_checks,
            failed_checks=failed_checks,
        )

    async def evaluate(self, dataset):
        results = []

        for case in dataset.cases:
            results.append(await self._evaluate_case(case))

        total = len(results)
        passed = sum(result.passed for result in results)
        metric_names = list(RecommendationCaseMetrics.model_fields.keys())

        averages = {
            name: (
                sum(
                    getattr(result.metrics, name)
                    for result in results
                ) / total
                if total else 0.0
            )
            for name in metric_names
        }

        return RecommendationEvaluationReport(
            dataset_name=dataset.dataset_name,
            dataset_version=dataset.version,
            total_cases=total,
            passed_cases=passed,
            failed_cases=total - passed,
            pass_rate=passed / total if total else 0.0,
            average_metrics=averages,
            results=results,
        )
