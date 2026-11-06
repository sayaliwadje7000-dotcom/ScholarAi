from __future__ import annotations

import time

from collections.abc import Callable
from typing import Any

from app.schemas.rag_evaluation import (
    RAGEvaluationCase,
    RAGEvaluationMetrics,
    RAGEvaluationReport,
    RAGEvaluationResult,
)

from app.services.rag.evaluation_metrics import (
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
    token_f1,
    required_term_coverage,
    citation_precision_recall,
    mean,
)


class RAGEvaluator:
    """
    Deterministic evaluation engine for ScholarAI RAG.

    Evaluates existing RAG results without modifying
    or invoking the production RAG pipeline.
    """

    def __init__(
        self,
        k: int = 5,
        minimum_recall: float = 0.60,
        minimum_answer_f1: float = 0.30,
        minimum_citation_precision: float = 0.80,
    ):

        if k <= 0:
            raise ValueError("k must be greater than zero")

        thresholds = {
            "minimum_recall": minimum_recall,
            "minimum_answer_f1": minimum_answer_f1,
            "minimum_citation_precision": minimum_citation_precision,
        }

        for name, value in thresholds.items():
            if not 0 <= value <= 1:
                raise ValueError(
                    f"{name} must be between 0 and 1"
                )

        self.k = k
        self.minimum_recall = minimum_recall
        self.minimum_answer_f1 = minimum_answer_f1
        self.minimum_citation_precision = minimum_citation_precision

    @staticmethod
    def _get_value(
        obj: Any,
        key: str,
        default: Any = None,
    ) -> Any:

        if isinstance(obj, dict):
            return obj.get(key, default)

        return getattr(obj, key, default)

    def evaluate_case(
        self,
        case: RAGEvaluationCase,
        rag_result: Any,
        latency_ms: float = 0.0,
    ) -> RAGEvaluationResult:

        if latency_ms < 0:
            raise ValueError("latency_ms cannot be negative")

        retrieved_chunks = self._get_value(
            rag_result,
            "retrieved_chunks",
            [],
        )

        retrieved_ids = [
            str(self._get_value(chunk, "chunk_id", ""))
            for chunk in retrieved_chunks
        ]

        retrieved_ids = [
            item for item in retrieved_ids if item
        ]

        answer = self._get_value(
            rag_result,
            "answer",
            "",
        )

        citations = self._get_value(
            rag_result,
            "citations",
            [],
        )

        actual_source_ids = [
            str(self._get_value(citation, "source_id", ""))
            for citation in citations
        ]

        actual_source_ids = [
            item for item in actual_source_ids if item
        ]

        grounding_status = self._get_value(
            rag_result,
            "grounding_status",
            "not_verified",
        )

        grounded = bool(
            self._get_value(rag_result, "grounded", False)
        )

        precision = precision_at_k(
            retrieved_ids,
            case.expected_chunk_ids,
            self.k,
        )

        recall = recall_at_k(
            retrieved_ids,
            case.expected_chunk_ids,
            self.k,
        )

        mrr = reciprocal_rank(
            retrieved_ids,
            case.expected_chunk_ids,
        )

        answer_f1 = (
            token_f1(answer, case.reference_answer)
            if case.reference_answer is not None
            else 0.0
        )

        term_coverage = required_term_coverage(
            answer,
            case.required_terms,
        )

        citation_precision, citation_recall = (
            citation_precision_recall(
                actual_source_ids,
                case.expected_citation_source_ids,
            )
        )

        abstention_correct = (
            grounding_status == "insufficient_evidence"
            if not case.answerable
            else grounding_status != "insufficient_evidence"
        )

        metrics = RAGEvaluationMetrics(
            precision_at_k=precision,
            recall_at_k=recall,
            reciprocal_rank=mrr,
            answer_f1=answer_f1,
            required_term_coverage=term_coverage,
            citation_precision=citation_precision,
            citation_recall=citation_recall,
            grounded=grounded,
            abstention_correct=abstention_correct,
            latency_ms=latency_ms,
        )

        failed_checks: list[str] = []

        if recall < self.minimum_recall:
            failed_checks.append("retrieval_recall")

        if (
            case.reference_answer is not None
            and answer_f1 < self.minimum_answer_f1
        ):
            failed_checks.append("answer_f1")

        if (
            case.expected_citation_source_ids
            and citation_precision < self.minimum_citation_precision
        ):
            failed_checks.append("citation_precision")

        if not abstention_correct:
            failed_checks.append("abstention")

        if case.answerable and not grounded:
            failed_checks.append("grounding")

        return RAGEvaluationResult(
            case_id=case.case_id,
            metrics=metrics,
            passed=not failed_checks,
            failed_checks=failed_checks,
        )

    def evaluate_dataset(
        self,
        dataset_name: str,
        cases: list[RAGEvaluationCase],
        runner: Callable[[RAGEvaluationCase], Any],
    ) -> RAGEvaluationReport:

        if not dataset_name:
            raise ValueError("dataset_name cannot be empty")

        if not cases:
            raise ValueError("Evaluation dataset cannot be empty")

        results: list[RAGEvaluationResult] = []

        for case in cases:
            started_at = time.perf_counter()

            rag_result = runner(case)

            if hasattr(rag_result, "__await__"):
                raise TypeError(
                    "Async runners are not supported. "
                    "Await the RAG result before evaluation."
                )

            latency_ms = (
                time.perf_counter() - started_at
            ) * 1000

            results.append(
                self.evaluate_case(
                    case=case,
                    rag_result=rag_result,
                    latency_ms=latency_ms,
                )
            )

        passed_cases = sum(
            result.passed for result in results
        )

        metric_names = (
            "precision_at_k",
            "recall_at_k",
            "reciprocal_rank",
            "answer_f1",
            "required_term_coverage",
            "citation_precision",
            "citation_recall",
        )

        average_metrics = {
            name: mean(
                getattr(result.metrics, name)
                for result in results
            )
            for name in metric_names
        }

        average_metrics["grounded_rate"] = mean(
            float(result.metrics.grounded)
            for result in results
        )

        average_metrics["abstention_accuracy"] = mean(
            float(result.metrics.abstention_correct)
            for result in results
        )

        average_metrics["average_latency_ms"] = mean(
            result.metrics.latency_ms
            for result in results
        )

        return RAGEvaluationReport(
            dataset_name=dataset_name,
            total_cases=len(results),
            passed_cases=passed_cases,
            failed_cases=len(results) - passed_cases,
            pass_rate=passed_cases / len(results),
            average_metrics=average_metrics,
            results=results,
        )
