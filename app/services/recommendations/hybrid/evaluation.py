from __future__ import annotations

from dataclasses import dataclass
from math import log2
from statistics import mean
from time import perf_counter
from types import MappingProxyType
from typing import Callable, Mapping, Sequence


class EvaluationError(Exception):
    """Base exception for recommendation evaluation."""


class EvaluationConfigurationError(EvaluationError):
    """Raised when evaluation configuration is invalid."""


class EvaluationDataError(EvaluationError):
    """Raised when evaluation data is invalid."""


class WeightExperimentError(EvaluationError):
    """Raised when a weight experiment cannot be executed."""


@dataclass(frozen=True, slots=True)
class EvaluationQuery:
    """
    One evaluation query with human-assigned relevance judgments.

    relevance:
        Maps resource identifiers to graded relevance values.

    catalog_ids:
        Optional catalog universe used for coverage calculation.
    """

    query_id: str

    relevance: Mapping[str, int]

    catalog_ids: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not self.query_id.strip():
            raise EvaluationDataError(
                "Evaluation query ID cannot be empty."
            )

        normalized = dict(self.relevance)

        for resource_id, relevance in normalized.items():
            if not resource_id:
                raise EvaluationDataError(
                    "Resource identifiers cannot be empty."
                )

            if isinstance(relevance, bool) or not isinstance(
                relevance, int
            ):
                raise EvaluationDataError(
                    "Relevance judgments must be integers."
                )

            if relevance < 0 or relevance > 3:
                raise EvaluationDataError(
                    "Relevance must be between 0 and 3."
                )

        if any(not resource_id for resource_id in self.catalog_ids):
            raise EvaluationDataError(
                "Catalog identifiers cannot be empty."
            )

        object.__setattr__(
            self,
            "relevance",
            MappingProxyType(normalized),
        )


@dataclass(frozen=True, slots=True)
class RecommendationMetrics:
    precision_at_k: float

    recall_at_k: float

    ndcg_at_k: float

    coverage: float

    duplicate_rate: float

    recommended_count: int

    unique_recommended_count: int

    relevant_count: int

    latency_ms: float | None = None

    def __post_init__(self) -> None:
        bounded_metrics = (
            self.precision_at_k,
            self.recall_at_k,
            self.ndcg_at_k,
            self.coverage,
            self.duplicate_rate,
        )

        for value in bounded_metrics:
            if not 0.0 <= value <= 1.0:
                raise EvaluationDataError(
                    "Evaluation metrics must be between 0 and 1."
                )

        if self.recommended_count < 0:
            raise EvaluationDataError(
                "Recommended count cannot be negative."
            )

        if self.unique_recommended_count < 0:
            raise EvaluationDataError(
                "Unique recommendation count cannot be negative."
            )

        if self.relevant_count < 0:
            raise EvaluationDataError(
                "Relevant count cannot be negative."
            )

        if self.latency_ms is not None and self.latency_ms < 0:
            raise EvaluationDataError(
                "Latency cannot be negative."
            )


@dataclass(frozen=True, slots=True)
class RankingEvaluationResult:
    strategy_name: str

    precision_at_k: float

    recall_at_k: float

    ndcg_at_k: float

    coverage: float

    duplicate_rate: float

    average_latency_ms: float | None

    evaluated_queries: int

    def __post_init__(self) -> None:
        if not self.strategy_name:
            raise EvaluationDataError(
                "Strategy name cannot be empty."
            )

        if self.evaluated_queries < 1:
            raise EvaluationDataError(
                "At least one query must be evaluated."
            )


class RecommendationEvaluator:
    """
    Evaluates recommendation rankings against relevance judgments.

    Metrics:
        Precision@K
        Recall@K
        NDCG@K
        Catalog coverage
        Duplicate rate
        Optional latency
    """

    def __init__(self, k: int = 10) -> None:
        if isinstance(k, bool) or not isinstance(k, int) or k < 1:
            raise EvaluationConfigurationError(
                "K must be a positive integer."
            )

        self.k = k

    @staticmethod
    def _validate_ranking(
        ranking: Sequence[str],
    ) -> None:
        for resource_id in ranking:
            if not isinstance(resource_id, str) or not resource_id:
                raise EvaluationDataError(
                    "Ranking contains an invalid resource identifier."
                )

    def precision_at_k(
        self,
        ranking: Sequence[str],
        relevance: Mapping[str, int],
    ) -> float:
        """
        Precision@K = relevant recommended resources / K.

        Missing recommendation slots are not treated as relevant.
        """

        self._validate_ranking(ranking)

        top_k = ranking[:self.k]

        relevant_recommendations = sum(
            1
            for resource_id in top_k
            if relevance.get(resource_id, 0) > 0
        )

        return relevant_recommendations / self.k

    def recall_at_k(
        self,
        ranking: Sequence[str],
        relevance: Mapping[str, int],
    ) -> float:
        """
        Recall@K = relevant recommended resources / all relevant resources.
        """

        self._validate_ranking(ranking)

        relevant_resources = {
            resource_id
            for resource_id, value in relevance.items()
            if value > 0
        }

        if not relevant_resources:
            return 0.0

        recommended_relevant = {
            resource_id
            for resource_id in ranking[:self.k]
            if resource_id in relevant_resources
        }

        return len(recommended_relevant) / len(relevant_resources)

    def dcg_at_k(
        self,
        ranking: Sequence[str],
        relevance: Mapping[str, int],
    ) -> float:
        """
        Discounted cumulative gain with graded relevance.
        """

        self._validate_ranking(ranking)

        score = 0.0

        for index, resource_id in enumerate(ranking[:self.k]):
            relevance_score = relevance.get(resource_id, 0)

            gain = (2 ** relevance_score) - 1

            discount = log2(index + 2)

            score += gain / discount

        return score

    def ndcg_at_k(
        self,
        ranking: Sequence[str],
        relevance: Mapping[str, int],
    ) -> float:
        """
        Normalized discounted cumulative gain.

        Measures ranking quality while giving more importance
        to highly relevant resources appearing near the top.
        """

        actual_dcg = self.dcg_at_k(
            ranking,
            relevance,
        )

        ideal_ranking = sorted(
            relevance.keys(),
            key=lambda resource_id: relevance[resource_id],
            reverse=True,
        )

        ideal_dcg = self.dcg_at_k(
            ideal_ranking,
            relevance,
        )

        if ideal_dcg == 0:
            return 0.0

        return actual_dcg / ideal_dcg

    @staticmethod
    def duplicate_rate(
        ranking: Sequence[str],
    ) -> float:
        """
        Duplicate rate = duplicate occurrences / total recommendations.
        """

        if not ranking:
            return 0.0

        duplicate_count = (
            len(ranking) - len(set(ranking))
        )

        return duplicate_count / len(ranking)

    @staticmethod
    def coverage(
        ranking: Sequence[str],
        catalog_ids: frozenset[str],
    ) -> float:
        """
        Coverage = unique recommended catalog resources / catalog size.
        """

        if not catalog_ids:
            return 0.0

        recommended = set(ranking)

        return len(recommended.intersection(catalog_ids)) / len(
            catalog_ids
        )

    def evaluate(
        self,
        ranking: Sequence[str],
        relevance: Mapping[str, int],
        catalog_ids: frozenset[str] = frozenset(),
        latency_ms: float | None = None,
    ) -> RecommendationMetrics:

        self._validate_ranking(ranking)

        if latency_ms is not None and latency_ms < 0:
            raise EvaluationDataError(
                "Latency cannot be negative."
            )

        return RecommendationMetrics(
            precision_at_k=self.precision_at_k(
                ranking,
                relevance,
            ),
            recall_at_k=self.recall_at_k(
                ranking,
                relevance,
            ),
            ndcg_at_k=self.ndcg_at_k(
                ranking,
                relevance,
            ),
            coverage=self.coverage(
                ranking,
                catalog_ids,
            ),
            duplicate_rate=self.duplicate_rate(
                ranking,
            ),
            recommended_count=len(ranking),
            unique_recommended_count=len(set(ranking)),
            relevant_count=sum(
                1 for value in relevance.values() if value > 0
            ),
            latency_ms=latency_ms,
        )

    def evaluate_strategy(
        self,
        strategy_name: str,
        rankings: Sequence[Sequence[str]],
        queries: Sequence[EvaluationQuery],
        latency_measurements: Sequence[float] | None = None,
    ) -> RankingEvaluationResult:

        if len(rankings) != len(queries):
            raise EvaluationDataError(
                "Ranking count must match evaluation query count."
            )

        if not rankings:
            raise EvaluationDataError(
                "At least one ranking is required."
            )

        if latency_measurements is not None:
            if len(latency_measurements) != len(rankings):
                raise EvaluationDataError(
                    "Latency measurement count must match rankings."
                )

        results = []

        for index, (ranking, query) in enumerate(
            zip(rankings, queries)
        ):
            latency = (
                latency_measurements[index]
                if latency_measurements is not None
                else None
            )

            results.append(
                self.evaluate(
                    ranking=ranking,
                    relevance=query.relevance,
                    catalog_ids=query.catalog_ids,
                    latency_ms=latency,
                )
            )

        average_latency = None

        if latency_measurements is not None:
            average_latency = mean(latency_measurements)

        return RankingEvaluationResult(
            strategy_name=strategy_name,
            precision_at_k=mean(
                result.precision_at_k for result in results
            ),
            recall_at_k=mean(
                result.recall_at_k for result in results
            ),
            ndcg_at_k=mean(
                result.ndcg_at_k for result in results
            ),
            coverage=mean(
                result.coverage for result in results
            ),
            duplicate_rate=mean(
                result.duplicate_rate for result in results
            ),
            average_latency_ms=average_latency,
            evaluated_queries=len(queries),
        )


# ============================================================
# COMPARATIVE EVALUATION
# ============================================================

@dataclass(frozen=True, slots=True)
class ComparativeEvaluationReport:

    results: Mapping[str, RankingEvaluationResult]

    best_strategy_by_ndcg: str

    best_strategy_by_precision: str

    lowest_latency_strategy: str | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "results",
            MappingProxyType(dict(self.results)),
        )


class ComparativeRecommendationEvaluator:

    def __init__(
        self,
        evaluator: RecommendationEvaluator,
    ) -> None:
        self.evaluator = evaluator

    def compare(
        self,
        rankings_by_strategy: Mapping[
            str,
            Sequence[Sequence[str]],
        ],
        queries: Sequence[EvaluationQuery],
        latency_by_strategy: Mapping[
            str,
            Sequence[float],
        ] | None = None,
    ) -> ComparativeEvaluationReport:

        if not rankings_by_strategy:
            raise EvaluationDataError(
                "At least one recommendation strategy is required."
            )

        results = {}

        for strategy_name, rankings in rankings_by_strategy.items():

            latency = (
                latency_by_strategy.get(strategy_name)
                if latency_by_strategy is not None
                else None
            )

            results[strategy_name] = (
                self.evaluator.evaluate_strategy(
                    strategy_name=strategy_name,
                    rankings=rankings,
                    queries=queries,
                    latency_measurements=latency,
                )
            )

        best_ndcg = max(
            results,
            key=lambda name: results[name].ndcg_at_k,
        )

        best_precision = max(
            results,
            key=lambda name: results[name].precision_at_k,
        )

        latency_candidates = {
            name: result.average_latency_ms
            for name, result in results.items()
            if result.average_latency_ms is not None
        }

        lowest_latency = (
            min(
                latency_candidates,
                key=latency_candidates.get,
            )
            if latency_candidates
            else None
        )

        return ComparativeEvaluationReport(
            results=results,
            best_strategy_by_ndcg=best_ndcg,
            best_strategy_by_precision=best_precision,
            lowest_latency_strategy=lowest_latency,
        )


# ============================================================
# RANKING CONSISTENCY
# ============================================================

@dataclass(frozen=True, slots=True)
class RankingConsistencyResult:

    agreement: float

    comparable_pairs: int


class RankingConsistencyEvaluator:

    @staticmethod
    def compare(
        first_ranking: Sequence[str],
        second_ranking: Sequence[str],
    ) -> RankingConsistencyResult:
        """
        Measures pairwise ordering agreement among shared resources.

        1.0 means complete agreement.
        0.0 means complete disagreement.

        Ties and pairs missing from either ranking are excluded.
        """

        first_positions = {
            resource_id: index
            for index, resource_id in enumerate(first_ranking)
        }

        second_positions = {
            resource_id: index
            for index, resource_id in enumerate(second_ranking)
        }

        shared = sorted(
            set(first_positions).intersection(second_positions)
        )

        concordant = 0
        comparable = 0

        for index, first_id in enumerate(shared):
            for second_id in shared[index + 1:]:

                first_order = (
                    first_positions[first_id]
                    - first_positions[second_id]
                )

                second_order = (
                    second_positions[first_id]
                    - second_positions[second_id]
                )

                if first_order == 0 or second_order == 0:
                    continue

                comparable += 1

                if (first_order > 0) == (second_order > 0):
                    concordant += 1

        agreement = (
            concordant / comparable
            if comparable
            else 0.0
        )

        return RankingConsistencyResult(
            agreement=agreement,
            comparable_pairs=comparable,
        )


# ============================================================
# WEIGHT EXPERIMENTS
# ============================================================

@dataclass(frozen=True, slots=True)
class WeightExperimentResult:

    weights: Mapping[str, float]

    ndcg_at_k: float

    precision_at_k: float

    recall_at_k: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "weights",
            MappingProxyType(dict(self.weights)),
        )


class HybridWeightExperimentRunner:
    """
    Runs controlled weight experiments.

    The ranking callback must return one ranked resource list
    per evaluation query.

    The callback is responsible for invoking the actual hybrid
    scoring/ranking pipeline with the supplied weights.
    """

    REQUIRED_COMPONENTS = frozenset(
        {
            "RULE_BASED",
            "CONTENT_BASED",
            "MACHINE_LEARNING",
        }
    )

    def __init__(
        self,
        evaluator: RecommendationEvaluator,
    ) -> None:
        self.evaluator = evaluator

    def validate_weights(
        self,
        weights: Mapping[str, float],
    ) -> None:

        if set(weights) != self.REQUIRED_COMPONENTS:
            raise WeightExperimentError(
                "Weights must define all three recommendation components."
            )

        for component, weight in weights.items():

            if isinstance(weight, bool) or not isinstance(
                weight,
                (int, float),
            ):
                raise WeightExperimentError(
                    f"Invalid weight for {component}."
                )

            if weight < 0 or weight > 1:
                raise WeightExperimentError(
                    f"Weight for {component} must be between 0 and 1."
                )

        if abs(sum(weights.values()) - 1.0) > 1e-9:
            raise WeightExperimentError(
                "Hybrid weights must sum to 1.0."
            )

    def run_experiment(
        self,
        weights: Mapping[str, float],
        queries: Sequence[EvaluationQuery],
        ranking_function: Callable[
            [Mapping[str, float], EvaluationQuery],
            Sequence[str],
        ],
    ) -> WeightExperimentResult:

        self.validate_weights(weights)

        if not queries:
            raise WeightExperimentError(
                "Evaluation queries cannot be empty."
            )

        rankings = []

        for query in queries:

            ranking = ranking_function(
                weights,
                query,
            )

            if not isinstance(ranking, Sequence):
                raise WeightExperimentError(
                    "Ranking function must return a sequence."
                )

            rankings.append(ranking)

        evaluation = self.evaluator.evaluate_strategy(
            strategy_name="hybrid_weight_experiment",
            rankings=rankings,
            queries=queries,
        )

        return WeightExperimentResult(
            weights=weights,
            ndcg_at_k=evaluation.ndcg_at_k,
            precision_at_k=evaluation.precision_at_k,
            recall_at_k=evaluation.recall_at_k,
        )

    def grid_search(
        self,
        configurations: Sequence[Mapping[str, float]],
        queries: Sequence[EvaluationQuery],
        ranking_function: Callable[
            [Mapping[str, float], EvaluationQuery],
            Sequence[str],
        ],
    ) -> tuple[WeightExperimentResult, ...]:

        if not configurations:
            raise WeightExperimentError(
                "At least one weight configuration is required."
            )

        results = []

        for weights in configurations:

            results.append(
                self.run_experiment(
                    weights=weights,
                    queries=queries,
                    ranking_function=ranking_function,
                )
            )

        return tuple(
            sorted(
                results,
                key=lambda result: (
                    result.ndcg_at_k,
                    result.precision_at_k,
                    result.recall_at_k,
                ),
                reverse=True,
            )
        )