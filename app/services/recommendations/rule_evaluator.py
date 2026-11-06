from dataclasses import dataclass
from typing import Any

from app.schemas.recommendation_rules import (
    RecommendationRule,
    RecommendationRuleConfiguration,
    RuleCondition,
    RuleEffect,
    RuleField,
    RuleOperator,
    RuleType,
)


@dataclass(frozen=True)
class RuleEvaluationResult:
    rule_id: str
    matched: bool
    effect: RuleEffect
    adjustment: float | None


@dataclass(frozen=True)
class RuleExecutionResult:
    eligible: bool
    exclusion_reason: str | None
    matched_rules: tuple[str, ...]
    evaluations: tuple[RuleEvaluationResult, ...]
    adjusted_score: float


class RuleEvaluator:
    """
    Evaluates declarative recommendation rules.

    Rules operate only on explicitly allowlisted fields.
    No arbitrary expressions or executable configuration are accepted.
    """

    def __init__(
        self,
        configuration: RecommendationRuleConfiguration,
    ):
        if not isinstance(
            configuration,
            RecommendationRuleConfiguration,
        ):
            raise TypeError(
                "Expected RecommendationRuleConfiguration."
            )

        self.configuration = configuration

    @staticmethod
    def _read_field(
        field: RuleField,
        resource: Any,
        context: Any,
    ):
        resource_fields = {
            RuleField.RESOURCE_TYPE: "resource_type",
            RuleField.SUBJECT: "subject",
            RuleField.DIFFICULTY: "difficulty",
            RuleField.LANGUAGE: "language",
            RuleField.QUALITY_SCORE: "quality_score",
            RuleField.CATEGORY_SLUGS: "category_slugs",
            RuleField.TOPICS: "topics",
            RuleField.KEYWORDS: "keywords",
            RuleField.LEARNING_OBJECTIVES: "learning_objectives",
            RuleField.PREREQUISITES: "prerequisites",
            RuleField.ESTIMATED_DURATION_MINUTES:
                "estimated_duration_minutes",
            RuleField.ESTIMATED_READING_MINUTES:
                "estimated_reading_minutes",
            RuleField.IS_BEGINNER_FRIENDLY:
                "is_beginner_friendly",
        }

        context_fields = {
            RuleField.PREFERRED_LANGUAGE: "preferred_language",
            RuleField.PREFERRED_SUBJECTS: "preferred_subjects",
            RuleField.LEARNING_GOALS: "learning_goals",
            RuleField.EDUCATION_LEVEL: "education_level",
        }

        if field in resource_fields:
            return getattr(
                resource,
                resource_fields[field],
                None,
            )

        if field in context_fields:
            return getattr(
                context,
                context_fields[field],
                None,
            )

        raise ValueError(
            f"Unsupported rule field: {field}"
        )

    @staticmethod
    def _normalize_string(value):
        if isinstance(value, str):
            return value.casefold().strip()

        return value

    @classmethod
    def _compare_values(
        cls,
        actual,
        expected,
        operator: RuleOperator,
    ) -> bool:
        """
        Compare values using deterministic, type-aware semantics.

        Missing actual values do not match ordinary comparisons.
        EXISTS is the exception.
        """

        if operator == RuleOperator.EXISTS:
            exists = actual is not None
            return exists is expected

        if actual is None:
            return False

        actual_normalized = cls._normalize_string(actual)

        expected_normalized = (
            cls._normalize_string(expected)
        )

        if operator == RuleOperator.EQUALS:
            return actual_normalized == expected_normalized

        if operator == RuleOperator.NOT_EQUALS:
            return actual_normalized != expected_normalized

        if operator == RuleOperator.IN:
            return actual_normalized in [
                cls._normalize_string(value)
                for value in expected
            ]

        if operator == RuleOperator.NOT_IN:
            return actual_normalized not in [
                cls._normalize_string(value)
                for value in expected
            ]

        if operator == RuleOperator.CONTAINS:
            if isinstance(actual, (list, tuple, set)):
                actual_values = [
                    cls._normalize_string(value)
                    for value in actual
                ]

                if isinstance(expected, list):
                    return all(
                        cls._normalize_string(value)
                        in actual_values
                        for value in expected
                    )

                return expected_normalized in actual_values

            if isinstance(actual, str):
                if isinstance(expected, list):
                    return all(
                        cls._normalize_string(value)
                        in actual_normalized
                        for value in expected
                    )

                return expected_normalized in actual_normalized

            return False

        if operator == RuleOperator.NOT_CONTAINS:
            return not cls._compare_values(
                actual,
                expected,
                RuleOperator.CONTAINS,
            )

        if isinstance(actual, bool) or isinstance(expected, bool):
            return False

        if operator == RuleOperator.GREATER_THAN:
            return actual > expected

        if operator == RuleOperator.GREATER_THAN_OR_EQUAL:
            return actual >= expected

        if operator == RuleOperator.LESS_THAN:
            return actual < expected

        if operator == RuleOperator.LESS_THAN_OR_EQUAL:
            return actual <= expected

        return False

    def evaluate_condition(
        self,
        condition: RuleCondition,
        resource,
        context,
    ) -> bool:
        actual = self._read_field(
            condition.field,
            resource,
            context,
        )

        return self._compare_values(
            actual,
            condition.value,
            condition.operator,
        )

    def evaluate_rule(
        self,
        rule: RecommendationRule,
        resource,
        context,
    ) -> RuleEvaluationResult:
        matched = self.evaluate_condition(
            rule.condition,
            resource,
            context,
        )

        return RuleEvaluationResult(
            rule_id=rule.rule_id,
            matched=matched,
            effect=rule.effect,
            adjustment=rule.adjustment,
        )

    @staticmethod
    def _apply_adjustment(
        score: float,
        evaluation: RuleEvaluationResult,
    ) -> float:
        if not evaluation.matched:
            return score

        adjustment = evaluation.adjustment

        if adjustment is None:
            return score

        if evaluation.effect == RuleEffect.ADD_SCORE:
            score += adjustment

        elif evaluation.effect == RuleEffect.SUBTRACT_SCORE:
            score -= adjustment

        elif evaluation.effect == RuleEffect.MULTIPLY_SCORE:
            score *= adjustment

        return max(0.0, min(1.0, score))

    def execute(
        self,
        resource,
        context,
        initial_score: float = 0.0,
    ) -> RuleExecutionResult:
        """
        Evaluate all enabled rules.

        Eligibility semantics:

        - EXCLUSION rules reject matching resources.
        - ELIGIBILITY + EXCLUDE rejects matching resources.
        - If at least one ELIGIBILITY + INCLUDE rule exists,
          a resource must match at least one of those rules.
        - Scoring adjustments are applied only to eligible resources.

        Lower priority values are evaluated first.
        """

        if isinstance(initial_score, bool) or not isinstance(
            initial_score,
            (int, float),
        ):
            raise TypeError(
                "initial_score must be numeric."
            )

        if not 0.0 <= initial_score <= 1.0:
            raise ValueError(
                "initial_score must be between 0 and 1."
            )

        rules = self.configuration.enabled_rules

        evaluations = tuple(
            self.evaluate_rule(
                rule,
                resource,
                context,
            )
            for rule in rules
        )

        evaluation_by_id = {
            result.rule_id: result
            for result in evaluations
        }

        matched_rules = tuple(
            result.rule_id
            for result in evaluations
            if result.matched
        )

        inclusion_rules = [
            rule
            for rule in rules
            if (
                rule.rule_type == RuleType.ELIGIBILITY
                and rule.effect == RuleEffect.INCLUDE
            )
        ]

        exclusion_rules = [
            rule
            for rule in rules
            if (
                rule.rule_type == RuleType.EXCLUSION
                or (
                    rule.rule_type == RuleType.ELIGIBILITY
                    and rule.effect == RuleEffect.EXCLUDE
                )
            )
        ]

        matched_exclusion = next(
            (
                rule
                for rule in exclusion_rules
                if evaluation_by_id[rule.rule_id].matched
            ),
            None,
        )

        if matched_exclusion is not None:
            return RuleExecutionResult(
                eligible=False,
                exclusion_reason=matched_exclusion.rule_id,
                matched_rules=matched_rules,
                evaluations=evaluations,
                adjusted_score=0.0,
            )

        if inclusion_rules:
            has_matching_inclusion = any(
                evaluation_by_id[rule.rule_id].matched
                for rule in inclusion_rules
            )

            if not has_matching_inclusion:
                return RuleExecutionResult(
                    eligible=False,
                    exclusion_reason="no_matching_eligibility_rule",
                    matched_rules=matched_rules,
                    evaluations=evaluations,
                    adjusted_score=0.0,
                )

        score = float(initial_score)

        for rule in rules:
            if rule.rule_type not in {
                RuleType.SCORING,
                RuleType.BOOST,
                RuleType.PENALTY,
            }:
                continue

            score = self._apply_adjustment(
                score,
                evaluation_by_id[rule.rule_id],
            )

        return RuleExecutionResult(
            eligible=True,
            exclusion_reason=None,
            matched_rules=matched_rules,
            evaluations=evaluations,
            adjusted_score=score,
        )