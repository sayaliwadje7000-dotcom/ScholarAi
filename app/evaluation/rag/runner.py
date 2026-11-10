import asyncio
import time

from collections.abc import Sequence
from typing import Any

from app.evaluation.rag.adapters import CallableRAGAdapter
from app.evaluation.rag.schemas import (
    RAGBenchmarkCaseOutcome,
    RAGBenchmarkConfig,
    RAGBenchmarkReport,
)

from app.schemas.rag_evaluation import (
    RAGEvaluationCase,
    RAGEvaluationDataset,
)

from app.services.rag.evaluation import RAGEvaluator


class RAGBenchmarkRunner:
    """
    Executes RAG benchmark datasets against an injected pipeline.

    Reuses ScholarAI's existing RAGEvaluator for answer quality,
    retrieval recall, citations, grounding and abstention checks.
    """

    def __init__(
        self,
        adapter: CallableRAGAdapter,
        config: RAGBenchmarkConfig | None = None,
    ):
        if not isinstance(adapter, CallableRAGAdapter):
            raise TypeError(
                "adapter must be a CallableRAGAdapter"
            )

        self.adapter = adapter
        self.config = config or RAGBenchmarkConfig()

        self.evaluator = RAGEvaluator(
            k=self.config.k,
            minimum_recall=self.config.minimum_recall,
            minimum_answer_f1=self.config.minimum_answer_f1,
            minimum_citation_precision=(
                self.config.minimum_citation_precision
            ),
        )

    @staticmethod
    def _get_value(
        obj: Any,
        key: str,
        default: Any = None,
    ) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)

        return getattr(obj, key, default)

    def _calculate_ranking_metrics(
        self,
        case: RAGEvaluationCase,
        rag_result: Any,
    ) -> dict[str, float]:
        chunks = self._get_value(
            rag_result,
            "retrieved_chunks",
            [],
        )

        retrieved_ids = [
            str(self._get_value(chunk, "chunk_id", ""))
            for chunk in chunks
        ]

        retrieved_ids = [
            item for item in retrieved_ids if item
        ]

        expected_ids = set(case.expected_chunk_ids)

        if not expected_ids:
            return {
                "ndcg_at_k": 1.0 if not retrieved_ids else 0.0,
                "hit_rate_at_k": 1.0 if not retrieved_ids else 0.0,
            }

        ranked = retrieved_ids[:self.config.k]

        relevance = [
            1.0 if item in expected_ids else 0.0
            for item in ranked
        ]

        dcg = sum(
            score / __import__("math").log2(index + 2)
            for index, score in enumerate(relevance)
        )

        ideal_count = min(
            len(expected_ids),
            self.config.k,
        )

        ideal_dcg = sum(
            1.0 / __import__("math").log2(index + 2)
            for index in range(ideal_count)
        )

        ndcg = (
            dcg / ideal_dcg
            if ideal_dcg > 0
            else 0.0
        )

        hit_rate = float(
            any(score > 0 for score in relevance)
        )

        return {
            "ndcg_at_k": ndcg,
            "hit_rate_at_k": hit_rate,
        }

    async def _run_case(
        self,
        case: RAGEvaluationCase,
        semaphore: asyncio.Semaphore,
    ) -> RAGBenchmarkCaseOutcome:
        async with semaphore:
            started = time.perf_counter()

            try:
                rag_result = await asyncio.wait_for(
                    self.adapter.run(case),
                    timeout=self.config.timeout_seconds,
                )

                latency_ms = (
                    time.perf_counter() - started
                ) * 1000

                evaluation_result = self.evaluator.evaluate_case(
                    case=case,
                    rag_result=rag_result,
                    latency_ms=latency_ms,
                )

                retrieval_metrics = (
                    self._calculate_ranking_metrics(
                        case,
                        rag_result,
                    )
                )

                return RAGBenchmarkCaseOutcome(
                    case_id=case.case_id,
                    result=evaluation_result,
                    latency_ms=latency_ms,
                    retrieval_metrics=retrieval_metrics,
                )

            except Exception as exc:
                latency_ms = (
                    time.perf_counter() - started
                ) * 1000

                return RAGBenchmarkCaseOutcome(
                    case_id=case.case_id,
                    latency_ms=latency_ms,
                    error=f"{type(exc).__name__}: {exc}",
                )

    @staticmethod
    def _build_report(
        dataset_name: str,
        outcomes: Sequence[RAGBenchmarkCaseOutcome],
    ) -> RAGBenchmarkReport:
        total = len(outcomes)

        passed = sum(
            outcome.status == "passed"
            for outcome in outcomes
        )

        errors = sum(
            outcome.status == "error"
            for outcome in outcomes
        )

        failed = total - passed - errors

        valid_outcomes = [
            outcome
            for outcome in outcomes
            if outcome.result is not None
        ]

        metric_names = (
            "precision_at_k",
            "recall_at_k",
            "reciprocal_rank",
            "answer_f1",
            "required_term_coverage",
            "citation_precision",
            "citation_recall",
            "latency_ms",
        )

        average_metrics = {}

        for name in metric_names:
            values = [
                float(getattr(outcome.result.metrics, name))
                for outcome in valid_outcomes
            ]

            average_metrics[name] = (
                sum(values) / len(values)
                if values else 0.0
            )

        for name in ("ndcg_at_k", "hit_rate_at_k"):
            values = [
                outcome.retrieval_metrics[name]
                for outcome in valid_outcomes
                if name in outcome.retrieval_metrics
            ]

            average_metrics[name] = (
                sum(values) / len(values)
                if values else 0.0
            )

        average_metrics["grounded_rate"] = (
            sum(
                float(outcome.result.metrics.grounded)
                for outcome in valid_outcomes
            ) / len(valid_outcomes)
            if valid_outcomes else 0.0
        )

        average_metrics["abstention_accuracy"] = (
            sum(
                float(outcome.result.metrics.abstention_correct)
                for outcome in valid_outcomes
            ) / len(valid_outcomes)
            if valid_outcomes else 0.0
        )

        return RAGBenchmarkReport(
            dataset_name=dataset_name,
            total_cases=total,
            passed_cases=passed,
            failed_cases=failed,
            error_cases=errors,
            pass_rate=passed / total if total else 0.0,
            average_metrics=average_metrics,
            outcomes=list(outcomes),
        )

    async def run(
        self,
        dataset: RAGEvaluationDataset,
    ) -> RAGBenchmarkReport:
        if not isinstance(dataset, RAGEvaluationDataset):
            raise TypeError(
                "dataset must be a RAGEvaluationDataset"
            )

        if not dataset.cases:
            raise ValueError(
                "Cannot evaluate an empty RAG dataset"
            )

        case_ids = [
            case.case_id for case in dataset.cases
        ]

        if len(case_ids) != len(set(case_ids)):
            raise ValueError(
                "Dataset case IDs must be unique"
            )

        semaphore = asyncio.Semaphore(
            self.config.max_concurrency
        )

        outcomes = await asyncio.gather(
            *[
                self._run_case(case, semaphore)
                for case in dataset.cases
            ]
        )

        return self._build_report(
            dataset_name=dataset.dataset_name,
            outcomes=outcomes,
        )
