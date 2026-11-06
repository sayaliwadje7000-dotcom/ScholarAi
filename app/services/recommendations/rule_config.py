from app.schemas.recommendation_rules import (
    RecommendationRule,
    RecommendationRuleConfiguration,
    RuleCondition,
    RuleEffect,
    RuleField,
    RuleOperator,
    RuleType,
)


class RecommendationRuleRegistry:
    """
    Central registry for recommendation rule configuration.

    The registry manages rule definitions and configuration versions.

    It does not evaluate rules or calculate recommendation scores.
    """

    def __init__(
        self,
        configuration: RecommendationRuleConfiguration | None = None,
    ):
        self._configuration = (
            configuration
            or self.default_configuration()
        )

    @staticmethod
    def default_configuration() -> RecommendationRuleConfiguration:
        """
        Return the initial versioned recommendation configuration.

        The initial configuration intentionally contains no active
        recommendation rules. Rules will be introduced explicitly
        as their behavior is implemented and tested.
        """

        return RecommendationRuleConfiguration(
            configuration_version="v1",
            rules=(),
        )

    @property
    def configuration(self) -> RecommendationRuleConfiguration:
        return self._configuration

    def get_enabled_rules(self) -> tuple[RecommendationRule, ...]:
        return self._configuration.enabled_rules

    def get_disabled_rules(self) -> tuple[RecommendationRule, ...]:
        return self._configuration.disabled_rules

    def get_rule(self, rule_id: str) -> RecommendationRule | None:
        for rule in self._configuration.rules:
            if rule.rule_id == rule_id:
                return rule

        return None

    def replace_configuration(
        self,
        configuration: RecommendationRuleConfiguration,
    ) -> None:
        """
        Replace the active configuration atomically.

        Validation occurs when the Pydantic configuration is created.
        The registry does not partially update individual rules.
        """

        if not isinstance(
            configuration,
            RecommendationRuleConfiguration,
        ):
            raise TypeError(
                "Expected RecommendationRuleConfiguration."
            )

        self._configuration = configuration

    def register_rule(
        self,
        rule: RecommendationRule,
    ) -> None:
        """
        Register a rule while preserving configuration integrity.
        """

        if not isinstance(rule, RecommendationRule):
            raise TypeError(
                "Expected RecommendationRule."
            )

        if self.get_rule(rule.rule_id) is not None:
            raise ValueError(
                f"Rule '{rule.rule_id}' is already registered."
            )

        updated_rules = (
            *self._configuration.rules,
            rule,
        )

        updated_configuration = (
            RecommendationRuleConfiguration(
                configuration_version=(
                    self._configuration.configuration_version
                ),
                rules=updated_rules,
            )
        )

        self._configuration = updated_configuration

    def remove_rule(self, rule_id: str) -> bool:
        """
        Remove a rule by its unique identifier.

        Returns False when the rule does not exist.
        """

        existing_rule = self.get_rule(rule_id)

        if existing_rule is None:
            return False

        updated_rules = tuple(
            rule
            for rule in self._configuration.rules
            if rule.rule_id != rule_id
        )

        self._configuration = (
            RecommendationRuleConfiguration(
                configuration_version=(
                    self._configuration.configuration_version
                ),
                rules=updated_rules,
            )
        )

        return True


def build_example_rules() -> RecommendationRuleConfiguration:
    """
    Construct an example configuration for testing and documentation.

    These rules are definitions only. They are not automatically
    installed as production recommendation behavior.
    """

    rules = (
        RecommendationRule(
            rule_id="resource.quality.minimum",
            name="Minimum Resource Quality",
            description=(
                "Exclude resources with a quality score below the "
                "configured threshold."
            ),
            rule_type=RuleType.ELIGIBILITY,
            priority=10,
            enabled=True,
            condition=RuleCondition(
                field=RuleField.QUALITY_SCORE,
                operator=RuleOperator.LESS_THAN,
                value=2.5,
            ),
            effect=RuleEffect.EXCLUDE,
        ),

        RecommendationRule(
            rule_id="resource.language.preference",
            name="Preferred Language Boost",
            description=(
                "Increase the recommendation score when a resource "
                "matches the preferred language."
            ),
            rule_type=RuleType.BOOST,
            priority=30,
            enabled=True,
            condition=RuleCondition(
                field=RuleField.LANGUAGE,
                operator=RuleOperator.EQUALS,
                value="english",
            ),
            effect=RuleEffect.ADD_SCORE,
            adjustment=0.10,
        ),

        RecommendationRule(
            rule_id="resource.beginner.penalty",
            name="Advanced Resource Penalty",
            description=(
                "Reduce the recommendation score for advanced "
                "resources when the configured condition matches."
            ),
            rule_type=RuleType.PENALTY,
            priority=40,
            enabled=False,
            condition=RuleCondition(
                field=RuleField.DIFFICULTY,
                operator=RuleOperator.EQUALS,
                value="advanced",
            ),
            effect=RuleEffect.SUBTRACT_SCORE,
            adjustment=0.10,
        ),
    )

    return RecommendationRuleConfiguration(
        configuration_version="v1",
        rules=rules,
    )