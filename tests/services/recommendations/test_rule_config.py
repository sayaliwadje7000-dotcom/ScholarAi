import pytest

from app.schemas.recommendation_rules import (
    RecommendationRule,
    RecommendationRuleConfiguration,
    RuleCondition,
    RuleEffect,
    RuleField,
    RuleOperator,
    RuleType,
)

from app.services.recommendations.rule_config import (
    RecommendationRuleRegistry,
    build_example_rules,
)


@pytest.fixture
def sample_condition():
    return RuleCondition(
        field=RuleField.QUALITY_SCORE,
        operator=RuleOperator.GREATER_THAN_OR_EQUAL,
        value=3.0,
    )


@pytest.fixture
def sample_rule(sample_condition):
    return RecommendationRule(
        rule_id="resource.quality.minimum",
        name="Minimum Resource Quality",
        description="Require an acceptable resource quality score.",
        rule_type=RuleType.ELIGIBILITY,
        priority=10,
        enabled=True,
        condition=sample_condition,
        effect=RuleEffect.INCLUDE,
    )


def test_rule_condition_creation(sample_condition):
    assert sample_condition.field == RuleField.QUALITY_SCORE

    assert (
        sample_condition.operator
        == RuleOperator.GREATER_THAN_OR_EQUAL
    )

    assert sample_condition.value == 3.0


def test_rule_condition_rejects_invalid_field():
    with pytest.raises(ValueError):
        RuleCondition(
            field="arbitrary_python_expression",
            operator=RuleOperator.EQUALS,
            value="test",
        )


def test_rule_condition_rejects_invalid_operator():
    with pytest.raises(ValueError):
        RuleCondition(
            field=RuleField.QUALITY_SCORE,
            operator="execute",
            value=3,
        )


def test_rule_condition_requires_list_for_in_operator():
    with pytest.raises(ValueError):
        RuleCondition(
            field=RuleField.RESOURCE_TYPE,
            operator=RuleOperator.IN,
            value="video",
        )


def test_rule_condition_rejects_empty_in_list():
    with pytest.raises(ValueError):
        RuleCondition(
            field=RuleField.RESOURCE_TYPE,
            operator=RuleOperator.IN,
            value=[],
        )


def test_rule_condition_requires_numeric_comparison_value():
    with pytest.raises(ValueError):
        RuleCondition(
            field=RuleField.QUALITY_SCORE,
            operator=RuleOperator.GREATER_THAN,
            value="high",
        )


def test_rule_condition_rejects_boolean_numeric_value():
    with pytest.raises(ValueError):
        RuleCondition(
            field=RuleField.QUALITY_SCORE,
            operator=RuleOperator.GREATER_THAN,
            value=True,
        )


def test_rule_condition_validates_exists_operator():
    with pytest.raises(ValueError):
        RuleCondition(
            field=RuleField.SUBJECT,
            operator=RuleOperator.EXISTS,
            value="yes",
        )


def test_rule_condition_accepts_exists_boolean():
    condition = RuleCondition(
        field=RuleField.SUBJECT,
        operator=RuleOperator.EXISTS,
        value=True,
    )

    assert condition.value is True


def test_recommendation_rule_creation(sample_rule):
    assert sample_rule.rule_id == "resource.quality.minimum"

    assert sample_rule.enabled is True

    assert sample_rule.priority == 10


def test_recommendation_rule_rejects_invalid_id(sample_condition):
    with pytest.raises(ValueError):
        RecommendationRule(
            rule_id="invalid rule id",
            name="Invalid Rule",
            description="This rule has an invalid identifier.",
            rule_type=RuleType.ELIGIBILITY,
            condition=sample_condition,
            effect=RuleEffect.INCLUDE,
        )


def test_recommendation_rule_rejects_missing_adjustment(sample_condition):
    with pytest.raises(ValueError):
        RecommendationRule(
            rule_id="resource.score.boost",
            name="Score Boost",
            description="Increase the recommendation score.",
            rule_type=RuleType.BOOST,
            condition=sample_condition,
            effect=RuleEffect.ADD_SCORE,
        )


def test_recommendation_rule_rejects_adjustment_above_one(
    sample_condition,
):
    with pytest.raises(ValueError):
        RecommendationRule(
            rule_id="resource.score.boost",
            name="Score Boost",
            description="Increase the recommendation score.",
            rule_type=RuleType.BOOST,
            condition=sample_condition,
            effect=RuleEffect.ADD_SCORE,
            adjustment=1.5,
        )


def test_recommendation_rule_rejects_adjustment_on_include(
    sample_condition,
):
    with pytest.raises(ValueError):
        RecommendationRule(
            rule_id="resource.include",
            name="Resource Inclusion",
            description="Include a matching resource.",
            rule_type=RuleType.ELIGIBILITY,
            condition=sample_condition,
            effect=RuleEffect.INCLUDE,
            adjustment=0.1,
        )


def test_exclusion_rule_requires_exclude_effect(sample_condition):
    with pytest.raises(ValueError):
        RecommendationRule(
            rule_id="resource.exclude",
            name="Resource Exclusion",
            description="Exclude matching resources.",
            rule_type=RuleType.EXCLUSION,
            condition=sample_condition,
            effect=RuleEffect.INCLUDE,
        )


def test_eligibility_rule_rejects_score_effect(sample_condition):
    with pytest.raises(ValueError):
        RecommendationRule(
            rule_id="resource.eligibility",
            name="Eligibility Rule",
            description="Check resource eligibility.",
            rule_type=RuleType.ELIGIBILITY,
            condition=sample_condition,
            effect=RuleEffect.ADD_SCORE,
            adjustment=0.1,
        )


def test_boost_rule_rejects_subtract_effect(sample_condition):
    with pytest.raises(ValueError):
        RecommendationRule(
            rule_id="resource.boost",
            name="Resource Boost",
            description="Boost matching resources.",
            rule_type=RuleType.BOOST,
            condition=sample_condition,
            effect=RuleEffect.SUBTRACT_SCORE,
            adjustment=0.1,
        )


def test_penalty_rule_requires_subtract_effect(sample_condition):
    with pytest.raises(ValueError):
        RecommendationRule(
            rule_id="resource.penalty",
            name="Resource Penalty",
            description="Penalize matching resources.",
            rule_type=RuleType.PENALTY,
            condition=sample_condition,
            effect=RuleEffect.ADD_SCORE,
            adjustment=0.1,
        )


def test_rule_configuration_defaults():
    configuration = RecommendationRuleConfiguration()

    assert configuration.configuration_version == "v1"

    assert configuration.rules == ()

    assert configuration.enabled_rules == ()


def test_rule_configuration_rejects_duplicate_ids(
    sample_rule,
):
    with pytest.raises(ValueError, match="unique"):
        RecommendationRuleConfiguration(
            rules=(
                sample_rule,
                sample_rule,
            )
        )


def test_rule_configuration_sorts_by_priority(sample_condition):
    low_priority = RecommendationRule(
        rule_id="resource.low",
        name="Low Priority",
        description="This rule has a lower execution priority.",
        rule_type=RuleType.ELIGIBILITY,
        priority=100,
        condition=sample_condition,
        effect=RuleEffect.INCLUDE,
    )

    high_priority = RecommendationRule(
        rule_id="resource.high",
        name="High Priority",
        description="This rule has a higher execution priority.",
        rule_type=RuleType.ELIGIBILITY,
        priority=10,
        condition=sample_condition,
        effect=RuleEffect.INCLUDE,
    )

    configuration = RecommendationRuleConfiguration(
        rules=(
            low_priority,
            high_priority,
        )
    )

    assert [
        rule.rule_id
        for rule in configuration.enabled_rules
    ] == [
        "resource.high",
        "resource.low",
    ]


def test_disabled_rules_are_not_in_enabled_rules(
    sample_condition,
):
    disabled_rule = RecommendationRule(
        rule_id="resource.disabled",
        name="Disabled Rule",
        description="This recommendation rule is disabled.",
        rule_type=RuleType.ELIGIBILITY,
        enabled=False,
        condition=sample_condition,
        effect=RuleEffect.INCLUDE,
    )

    configuration = RecommendationRuleConfiguration(
        rules=(disabled_rule,)
    )

    assert configuration.enabled_rules == ()

    assert len(configuration.disabled_rules) == 1


def test_registry_uses_default_configuration():
    registry = RecommendationRuleRegistry()

    assert registry.configuration.configuration_version == "v1"

    assert registry.get_enabled_rules() == ()


def test_registry_registers_rule(sample_rule):
    registry = RecommendationRuleRegistry()

    registry.register_rule(sample_rule)

    assert registry.get_rule(
        "resource.quality.minimum"
    ) == sample_rule


def test_registry_rejects_duplicate_registration(sample_rule):
    registry = RecommendationRuleRegistry()

    registry.register_rule(sample_rule)

    with pytest.raises(ValueError, match="already registered"):
        registry.register_rule(sample_rule)


def test_registry_returns_none_for_missing_rule():
    registry = RecommendationRuleRegistry()

    assert registry.get_rule("missing.rule") is None


def test_registry_removes_rule(sample_rule):
    registry = RecommendationRuleRegistry()

    registry.register_rule(sample_rule)

    result = registry.remove_rule(sample_rule.rule_id)

    assert result is True

    assert registry.get_rule(sample_rule.rule_id) is None


def test_registry_returns_false_when_removing_missing_rule():
    registry = RecommendationRuleRegistry()

    assert registry.remove_rule("missing.rule") is False


def test_registry_replaces_configuration(sample_rule):
    registry = RecommendationRuleRegistry()

    configuration = RecommendationRuleConfiguration(
        configuration_version="v2",
        rules=(sample_rule,),
    )

    registry.replace_configuration(configuration)

    assert registry.configuration.configuration_version == "v2"

    assert registry.get_rule(sample_rule.rule_id) == sample_rule


def test_registry_rejects_wrong_configuration_type():
    registry = RecommendationRuleRegistry()

    with pytest.raises(TypeError):
        registry.replace_configuration({})


def test_example_configuration_contains_valid_rules():
    configuration = build_example_rules()

    assert configuration.configuration_version == "v1"

    assert len(configuration.rules) == 3

    assert len(configuration.enabled_rules) == 2

    assert len(configuration.disabled_rules) == 1


def test_registry_rejects_wrong_rule_type():
    registry = RecommendationRuleRegistry()

    with pytest.raises(TypeError):
        registry.register_rule({})