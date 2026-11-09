from collections import defaultdict
from statistics import mean

from app.schemas.personalization_evaluation import (
    BaselineComparison,
    CalibrationMetrics,
    EvaluationFeedback,
    FeedbackMetrics,
    PersonalizationEvaluationRequest,
    PersonalizationEvaluationResponse,
    RankingMetrics,
    SegmentEvaluation,
)


class PersonalizationEvaluationService:
    """
    Offline evaluation service for personalized recommendations.

    This service does not:
    - modify recommendation rankings;
    - update user preferences;
    - persist evaluation results;
    - train recommendation models;
    - generate synthetic ground truth.

    It evaluates explicitly supplied evaluation cases.
    """

    @staticmethod
    def _precision_at_k(
        recommended: list[str],
        relevant: set[str],
        k: int,
    ) -> float:

        if k <= 0:
            return 0.0

        selected = recommended[:k]

        if not selected:
            return 0.0

        hits = sum(
            1
            for resource_id in selected
            if resource_id in relevant
        )

        return hits / k

    @staticmethod
    def _recall_at_k(
        recommended: list[str],
        relevant: set[str],
        k: int,
    ) -> float:

        if not relevant:
            return 0.0

        selected = recommended[:k]

        hits = sum(
            1
            for resource_id in selected
            if resource_id in relevant
        )

        return hits / len(relevant)

    @staticmethod
    def _dcg_at_k(
        recommended: list[str],
        relevant: set[str],
        k: int,
    ) -> float:

        score = 0.0

        for index, resource_id in enumerate(
            recommended[:k]
        ):
            relevance = (
                1.0
                if resource_id in relevant
                else 0.0
            )

            position = index + 1

            score += relevance / (
                __import__("math").log2(position + 1)
            )

        return score

    @classmethod
    def _ndcg_at_k(
        cls,
        recommended: list[str],
        relevant: set[str],
        k: int,
    ) -> float:

        if not relevant:
            return 0.0

        ideal_recommendations = [
            "relevant"
        ] * len(relevant)

        ideal_dcg = cls._dcg_at_k(
            recommended=ideal_recommendations,
            relevant={"relevant"},
            k=k,
        )

        if ideal_dcg == 0.0:
            return 0.0

        actual_dcg = cls._dcg_at_k(
            recommended=recommended,
            relevant=relevant,
            k=k,
        )

        return min(
            actual_dcg / ideal_dcg,
            1.0,
        )

    @staticmethod
    def _reciprocal_rank(
        recommended: list[str],
        relevant: set[str],
    ) -> float:

        for index, resource_id in enumerate(
            recommended
        ):
            if resource_id in relevant:
                return 1.0 / (index + 1)

        return 0.0

    @classmethod
    def _calculate_ranking_metrics(
        cls,
        recommended: list[str],
        relevant: set[str],
        k: int,
    ) -> RankingMetrics:

        return RankingMetrics(
            precision_at_k=cls._precision_at_k(
                recommended,
                relevant,
                k,
            ),
            recall_at_k=cls._recall_at_k(
                recommended,
                relevant,
                k,
            ),
            ndcg_at_k=cls._ndcg_at_k(
                recommended,
                relevant,
                k,
            ),
            reciprocal_rank=cls._reciprocal_rank(
                recommended,
                relevant,
            ),
        )

    @staticmethod
    def _calculate_feedback_metrics(
        cases,
    ) -> FeedbackMetrics:

        positive = 0
        negative = 0
        neutral = 0

        for case in cases:
            for feedback_value in case.feedback.values():

                if feedback_value == EvaluationFeedback.POSITIVE:
                    positive += 1

                elif feedback_value == EvaluationFeedback.NEGATIVE:
                    negative += 1

                elif feedback_value == EvaluationFeedback.NEUTRAL:
                    neutral += 1

        total = positive + negative + neutral

        explicit_feedback = positive + negative

        positive_rate = (
            positive / explicit_feedback
            if explicit_feedback
            else 0.0
        )

        return FeedbackMetrics(
            total_feedback=total,
            positive_feedback=positive,
            negative_feedback=negative,
            neutral_feedback=neutral,
            positive_feedback_rate=positive_rate,
        )

    @staticmethod
    def _calculate_calibration(
        cases,
        bins: int,
    ) -> CalibrationMetrics:

        if not cases:
            return CalibrationMetrics(
                brier_score=0.0,
                expected_calibration_error=0.0,
                evaluated_cases=0,
            )

        brier_scores = []

        bucket_values = defaultdict(list)

        for case in cases:

            # Observed utility proxy:
            # whether at least one relevant item appears
            # in the returned recommendation list.
            observed = float(
                any(
                    resource_id in case.relevant_resource_ids
                    for resource_id in case.recommended_resource_ids
                )
            )

            confidence = case.confidence

            brier_scores.append(
                (confidence - observed) ** 2
            )

            bucket_index = min(
                int(confidence * bins),
                bins - 1,
            )

            bucket_values[bucket_index].append(
                (confidence, observed)
            )

        brier_score = mean(brier_scores)

        expected_calibration_error = 0.0

        total_cases = len(cases)

        for bucket in bucket_values.values():

            average_confidence = mean(
                item[0]
                for item in bucket
            )

            average_observed = mean(
                item[1]
                for item in bucket
            )

            bucket_weight = (
                len(bucket) / total_cases
            )

            expected_calibration_error += (
                bucket_weight
                * abs(
                    average_confidence
                    - average_observed
                )
            )

        return CalibrationMetrics(
            brier_score=brier_score,
            expected_calibration_error=(
                expected_calibration_error
            ),
            evaluated_cases=total_cases,
        )

    @classmethod
    def _calculate_baseline_comparison(
        cls,
        cases,
    ):

        comparable_cases = [
            case
            for case in cases
            if case.baseline_resource_ids
        ]

        if not comparable_cases:
            return None

        personalized_ndcg = mean(
            cls._ndcg_at_k(
                case.recommended_resource_ids,
                case.relevant_resource_ids,
                5,
            )
            for case in comparable_cases
        )

        baseline_ndcg = mean(
            cls._ndcg_at_k(
                case.baseline_resource_ids,
                case.relevant_resource_ids,
                5,
            )
            for case in comparable_cases
        )

        personalized_precision = mean(
            cls._precision_at_k(
                case.recommended_resource_ids,
                case.relevant_resource_ids,
                5,
            )
            for case in comparable_cases
        )

        baseline_precision = mean(
            cls._precision_at_k(
                case.baseline_resource_ids,
                case.relevant_resource_ids,
                5,
            )
            for case in comparable_cases
        )

        return BaselineComparison(
            evaluated_cases=len(comparable_cases),
            personalized_ndcg=personalized_ndcg,
            baseline_ndcg=baseline_ndcg,
            ndcg_improvement=(
                personalized_ndcg - baseline_ndcg
            ),
            personalized_precision=personalized_precision,
            baseline_precision=baseline_precision,
            precision_improvement=(
                personalized_precision
                - baseline_precision
            ),
        )

    @classmethod
    def _calculate_segment_metrics(
        cls,
        cases,
    ):

        grouped_cases = defaultdict(list)

        for case in cases:
            grouped_cases[case.segment].append(case)

        results = []

        for segment, segment_cases in grouped_cases.items():

            ndcg_values = [
                cls._ndcg_at_k(
                    case.recommended_resource_ids,
                    case.relevant_resource_ids,
                    5,
                )
                for case in segment_cases
            ]

            precision_values = [
                cls._precision_at_k(
                    case.recommended_resource_ids,
                    case.relevant_resource_ids,
                    5,
                )
                for case in segment_cases
            ]

            confidence_values = [
                case.confidence
                for case in segment_cases
            ]

            results.append(
                SegmentEvaluation(
                    segment=segment,
                    evaluated_cases=len(segment_cases),
                    average_ndcg_at_5=mean(ndcg_values),
                    average_precision_at_5=mean(
                        precision_values
                    ),
                    average_confidence=mean(
                        confidence_values
                    ),
                )
            )

        return sorted(
            results,
            key=lambda item: item.segment.value,
        )

    @classmethod
    def evaluate(
        cls,
        request: PersonalizationEvaluationRequest,
    ) -> PersonalizationEvaluationResponse:

        cases = request.cases

        ranking_results = {}

        warnings = []

        for k in request.k_values:

            metrics = [
                cls._calculate_ranking_metrics(
                    case.recommended_resource_ids,
                    case.relevant_resource_ids,
                    k,
                )
                for case in cases
            ]

            ranking_results[f"@{k}"] = RankingMetrics(
                precision_at_k=mean(
                    item.precision_at_k
                    for item in metrics
                ),
                recall_at_k=mean(
                    item.recall_at_k
                    for item in metrics
                ),
                ndcg_at_k=mean(
                    item.ndcg_at_k
                    for item in metrics
                ),
                reciprocal_rank=mean(
                    item.reciprocal_rank
                    for item in metrics
                ),
            )

        cases_with_recommendations = sum(
            bool(case.recommended_resource_ids)
            for case in cases
        )

        recommendation_coverage = (
            cases_with_recommendations / len(cases)
        )

        feedback_metrics = (
            cls._calculate_feedback_metrics(cases)
        )

        calibration_metrics = (
            cls._calculate_calibration(
                cases,
                request.calibration_bins,
            )
        )

        baseline_comparison = (
            cls._calculate_baseline_comparison(cases)
        )

        segment_metrics = (
            cls._calculate_segment_metrics(cases)
        )

        if not any(
            case.relevant_resource_ids
            for case in cases
        ):
            warnings.append(
                "No ground-truth relevant resources were supplied. "
                "Ranking metrics cannot establish recommendation quality."
            )

        if not any(
            case.feedback
            for case in cases
        ):
            warnings.append(
                "No explicit feedback was supplied. "
                "Feedback metrics are not representative."
            )

        if baseline_comparison is None:
            warnings.append(
                "No baseline rankings were supplied. "
                "Personalized-versus-baseline comparison is unavailable."
            )

        if cases_with_recommendations == 0:
            warnings.append(
                "No recommendations were supplied in the evaluation cases."
            )

        return PersonalizationEvaluationResponse(
            total_cases=len(cases),
            cases_with_recommendations=(
                cases_with_recommendations
            ),
            recommendation_coverage=(
                recommendation_coverage
            ),
            ranking_metrics=ranking_results,
            calibration=calibration_metrics,
            feedback=feedback_metrics,
            baseline_comparison=baseline_comparison,
            segment_evaluations=segment_metrics,
            evaluation_warnings=warnings,
        )