from enum import Enum
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class RuleType(str, Enum):
    """
    Defines the purpose of a recommendation rule.
    """

    ELIGIBILITY = "eligibility"
    SCORING = "scoring"
    BOOST = "boost"
    PENALTY = "penalty"
    EXCLUSION = "exclusion"


class RuleOperator(str, Enum):
    """
    Supported operators for declarative rule conditions.
    """

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"

    IN = "in"
    NOT_IN = "not_in"

    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"

    GREATER_THAN = "greater_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"

    LESS_THAN = "less_than"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"

    EXISTS = "exists"


class RuleEffect(str, Enum):
    """
    Describes the action associated with a matching rule.
    """

    INCLUDE = "include"
    EXCLUDE = "exclude"

    ADD_SCORE = "add_score"
    SUBTRACT_SCORE = "subtract_score"

    MULTIPLY_SCORE = "multiply_score"


class RuleField(str, Enum):
    """
    Allowlisted fields that recommendation rules may reference.

    These names correspond to resource classification and learning
    context attributes. They are not arbitrary Python expressions.
    """

    RESOURCE_TYPE = "resource_type"
    SUBJECT = "subject"
    DIFFICULTY = "difficulty"
    LANGUAGE = "language"

    QUALITY_SCORE = "quality_score"

    CATEGORY_SLUGS = "category_slugs"
    TOPICS = "topics"
    KEYWORDS = "keywords"

    LEARNING_OBJECTIVES = "learning_objectives"
    PREREQUISITES = "prerequisites"

    ESTIMATED_DURATION_MINUTES = "estimated_duration_minutes"
    ESTIMATED_READING_MINUTES = "estimated_reading_minutes"

    IS_BEGINNER_FRIENDLY = "is_beginner_friendly"

    PREFERRED_LANGUAGE = "preferred_language"
    PREFERRED_SUBJECTS = "preferred_subjects"
    LEARNING_GOALS = "learning_goals"
    EDUCATION_LEVEL = "education_level"


class RuleCondition(BaseModel):
    """
    Declarative condition used by a recommendation rule.

    Conditions are represented as structured data rather than
    executable Python expressions.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    field: RuleField

    operator: RuleOperator

    value: Any = None

    @model_validator(mode="after")
    def validate_operator_value(self):
        collection_operators = {
            RuleOperator.IN,
            RuleOperator.NOT_IN,
        }

        comparison_operators = {
            RuleOperator.GREATER_THAN,
            RuleOperator.GREATER_THAN_OR_EQUAL,
            RuleOperator.LESS_THAN,
            RuleOperator.LESS_THAN_OR_EQUAL,
        }

        if self.operator in collection_operators:
            if not isinstance(self.value, list):
                raise ValueError(
                    "IN and NOT_IN operators require a list value."
                )

            if not self.value:
                raise ValueError(
                    "IN and NOT_IN operators cannot use an empty list."
                )

        elif self.operator in comparison_operators:
            if isinstance(self.value, bool) or not isinstance(
                self.value,
                (int, float),
            ):
                raise ValueError(
                    "Numeric comparison operators require a numeric value."
                )

        elif self.operator in {
            RuleOperator.CONTAINS,
            RuleOperator.NOT_CONTAINS,
        }:
            if not isinstance(self.value, (str, list)):
                raise ValueError(
                    "CONTAINS operators require a string or list value."
                )

            if isinstance(self.value, str) and not self.value.strip():
                raise ValueError(
                    "CONTAINS operators cannot use an empty string."
                )

            if isinstance(self.value, list) and not self.value:
                raise ValueError(
                    "CONTAINS operators cannot use an empty list."
                )

        elif self.operator == RuleOperator.EXISTS:
            if not isinstance(self.value, bool):
                raise ValueError(
                    "EXISTS operator requires a boolean value."
                )

        elif self.operator in {
            RuleOperator.EQUALS,
            RuleOperator.NOT_EQUALS,
        }:
            if self.value is None:
                raise ValueError(
                    "Equality operators require a non-null value."
                )

        return self


class RecommendationRule(BaseModel):
    """
    Complete recommendation rule definition.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        frozen=True,
    )

    rule_id: str = Field(
        min_length=3,
        max_length=100,
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$",
    )

    name: str = Field(
        min_length=3,
        max_length=150,
    )

    description: str = Field(
        min_length=10,
        max_length=1000,
    )

    rule_type: RuleType

    priority: int = Field(
        default=100,
        ge=1,
        le=10000,
    )

    enabled: bool = True

    condition: RuleCondition

    effect: RuleEffect

    adjustment: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )

    @model_validator(mode="after")
    def validate_effect_configuration(self):
        adjustment_effects = {
            RuleEffect.ADD_SCORE,
            RuleEffect.SUBTRACT_SCORE,
            RuleEffect.MULTIPLY_SCORE,
        }

        if self.effect in adjustment_effects:
            if self.adjustment is None:
                raise ValueError(
                    "Score adjustment effects require an adjustment value."
                )

        elif self.adjustment is not None:
            raise ValueError(
                "Adjustment must only be provided for score effects."
            )

        if (
            self.rule_type == RuleType.EXCLUSION
            and self.effect != RuleEffect.EXCLUDE
        ):
            raise ValueError(
                "EXCLUSION rules must use the EXCLUDE effect."
            )

        if (
            self.rule_type == RuleType.ELIGIBILITY
            and self.effect not in {
                RuleEffect.INCLUDE,
                RuleEffect.EXCLUDE,
            }
        ):
            raise ValueError(
                "ELIGIBILITY rules must use INCLUDE or EXCLUDE."
            )

        if (
            self.rule_type == RuleType.BOOST
            and self.effect not in {
                RuleEffect.ADD_SCORE,
                RuleEffect.MULTIPLY_SCORE,
            }
        ):
            raise ValueError(
                "BOOST rules must use ADD_SCORE or MULTIPLY_SCORE."
            )

        if (
            self.rule_type == RuleType.PENALTY
            and self.effect != RuleEffect.SUBTRACT_SCORE
        ):
            raise ValueError(
                "PENALTY rules must use SUBTRACT_SCORE."
            )

        if (
            self.rule_type == RuleType.SCORING
            and self.effect not in adjustment_effects
        ):
            raise ValueError(
                "SCORING rules must use a score adjustment effect."
            )

        return self


class RecommendationRuleConfiguration(BaseModel):
    """
    Centralized configuration for the recommendation engine.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    configuration_version: str = Field(
        default="v1",
        min_length=1,
        max_length=50,
    )

    rules: tuple[RecommendationRule, ...] = Field(
        default_factory=tuple,
    )

    @model_validator(mode="after")
    def validate_unique_rule_ids(self):
        rule_ids = [
            rule.rule_id
            for rule in self.rules
        ]

        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError(
                "Recommendation rule IDs must be unique."
            )

        return self

    @property
    def enabled_rules(self) -> tuple[RecommendationRule, ...]:
        """
        Return enabled rules in deterministic priority order.

        Lower priority values execute first.
        """
        return tuple(
            sorted(
                (
                    rule
                    for rule in self.rules
                    if rule.enabled
                ),
                key=lambda rule: (
                    rule.priority,
                    rule.rule_id,
                ),
            )
        )

    @property
    def disabled_rules(self) -> tuple[RecommendationRule, ...]:
        return tuple(
            rule
            for rule in self.rules
            if not rule.enabled
        )