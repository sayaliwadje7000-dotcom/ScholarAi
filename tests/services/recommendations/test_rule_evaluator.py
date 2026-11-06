from types import SimpleNamespace

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

from app.services.recommendations.rule_evaluator import (
    RuleEvaluator,
)


@pytest.fixture
def resource():
    return SimpleNamespace(
        resource_type="video",
        subject="Data Structures",
        difficulty="beginner",
        language="english",
        quality_score=4.5,
        category_slugs=["data-structures"],
        topics=["binary trees", "tree traversal"],
        keywords=["BST"],
        learning_objectives=["understand binary trees"],
        prerequisites=[],
        estimated_duration_minutes=25,
        estimated_reading_minutes=15,
        is_beginner_friendly=True,
    )


@pytest.fixture
def context():
    return SimpleNamespace(
        preferred_language="english",
        preferred_subjects=["Data Structures"],
        learning_goals=["understand algorithms"],
        education_level="Undergraduate",
    )


def make_rule(
    rule_id,
    rule_type,
    field,
    operator,
    value,
    effect,
    adjustment=None,
    priority=100,
):
    return RecommendationRule(
        rule_id=rule_id,
        name="Test Rule",
        description="A rule used for automated testing.",
        rule_type=rule_type,
        priority=priority,
        condition=RuleCondition(
            field=field,
            operator=operator,
            value=value,
        ),
        effect=effect,
        adjustment=adjustment,
    )


def test_rule_evaluator_matches_equals(resource, context):
    rule = make_rule(
        "test.language",
        RuleType.ELIGIBILITY,
        RuleField.LANGUAGE,
        RuleOperator.EQUALS,
        "ENGLISH",
        RuleEffect.INCLUDE,
    )

    evaluator = RuleEvaluator(
        RecommendationRuleConfiguration(
            rules=(rule,)
        )
    )

    assert evaluator.evaluate_rule(
        rule,
        resource,
        context,
    ).matched is True


def test_rule_evaluator_supports_not_equals(resource, context):
    rule = make_rule(
        "test.language",
        RuleType.ELIGIBILITY,
        RuleField.LANGUAGE,
        RuleOperator.NOT_EQUALS,
        "hindi",
        RuleEffect.INCLUDE,
    )

    evaluator = RuleEvaluator(
        RecommendationRuleConfiguration(
            rules=(rule,)
        )
    )

    assert evaluator.evaluate_rule(
        rule,
        resource,
        context,
    ).matched is True


def test_rule_evaluator_supports_in(resource, context):
    rule = make_rule(
        "test.type",
        RuleType.ELIGIBILITY,
        RuleField.RESOURCE_TYPE,
        RuleOperator.IN,
        ["video", "article"],
        RuleEffect.INCLUDE,
    )

    evaluator = RuleEvaluator(
        RecommendationRuleConfiguration(
            rules=(rule,)
        )
    )

    assert evaluator.evaluate_rule(
        rule,
        resource,
        context,
    ).matched is True


def test_rule_evaluator_supports_not_in(resource, context):
    rule = make_rule(
        "test.type",
        RuleType.ELIGIBILITY,
        RuleField.RESOURCE_TYPE,
        RuleOperator.NOT_IN,
        ["book", "course"],
        RuleEffect.INCLUDE,
    )

    evaluator = RuleEvaluator(
        RecommendationRuleConfiguration(
            rules=(rule,)
        )
    )

    assert evaluator.evaluate_rule(
        rule,
        resource,
        context,
    ).matched is True


def test_rule_evaluator_supports_contains(resource, context):
    rule = make_rule(
        "test.topic",
        RuleType.ELIGIBILITY,
        RuleField.TOPICS,
        RuleOperator.CONTAINS,
        "binary trees",
        RuleEffect.INCLUDE,
    )

    evaluator = RuleEvaluator(
        RecommendationRuleConfiguration(
            rules=(rule,)
        )
    )

    assert evaluator.evaluate_rule(
        rule,
        resource,
        context,
    ).matched is True


def test_rule_evaluator_supports_numeric_comparison(
    resource,
    context,
):
    rule = make_rule(
        "test.quality",
        RuleType.ELIGIBILITY,
        RuleField.QUALITY_SCORE,
        RuleOperator.GREATER_THAN_OR_EQUAL,
        4.0,
        RuleEffect.INCLUDE,
    )

    evaluator = RuleEvaluator(
        RecommendationRuleConfiguration(
            rules=(rule,)
        )
    )

    assert evaluator.evaluate_rule(
        rule,
        resource,
        context,
    ).matched is True


def test_rule_evaluator_supports_exists(resource, context):
    rule = make_rule(
        "test.subject",
        RuleType.ELIGIBILITY,
        RuleField.SUBJECT,
        RuleOperator.EXISTS,
        True,
        RuleEffect.INCLUDE,
    )

    evaluator = RuleEvaluator(
        RecommendationRuleConfiguration(
            rules=(rule,)
        )
    )

    assert evaluator.evaluate_rule(
        rule,
        resource,
        context,
    ).matched is True


def test_rule_evaluator_handles_missing_fields(context):
    resource = SimpleNamespace(
        quality_score=None,
    )

    rule = make_rule(
        "test.quality",
        RuleType.ELIGIBILITY,
        RuleField.QUALITY_SCORE,
        RuleOperator.EXISTS,
        False,
        RuleEffect.INCLUDE,
    )

    evaluator = RuleEvaluator(
        RecommendationRuleConfiguration(
            rules=(rule,)
        )
    )

    assert evaluator.evaluate_rule(
        rule,
        resource,
        context,
    ).matched is True


def test_rule_evaluator_excludes_matching_resource(
    resource,
    context,
):
    rule = make_rule(
        "test.exclude",
        RuleType.EXCLUSION,
        RuleField.QUALITY_SCORE,
        RuleOperator.LESS_THAN,
        3.0,
        RuleEffect.EXCLUDE,
    )

    evaluator = RuleEvaluator(
        RecommendationRuleConfiguration(
            rules=(rule,)
        )
    )

    result = evaluator.execute(
        resource,
        context,
        initial_score=0.8,
    )

    assert result.eligible is True


def test_rule_evaluator_excludes_low_quality_resource(
    resource,
    context,
):
    resource.quality_score = 2.0

    rule = make_rule(
        "test.exclude",
        RuleType.EXCLUSION,
        RuleField.QUALITY_SCORE,
        RuleOperator.LESS_THAN,
        3.0,
        RuleEffect.EXCLUDE,
    )

    evaluator = RuleEvaluator(
        RecommendationRuleConfiguration(
            rules=(rule,)
        )
    )

    result = evaluator.execute(
        resource,
        context,
        initial_score=0.8,
    )

    assert result.eligible is False

    assert result.adjusted_score == 0.0


def test_rule_evaluator_requires_matching_inclusion(
    resource,
    context,
):
    rule = make_rule(
        "test.inclusion",
        RuleType.ELIGIBILITY,
        RuleField.RESOURCE_TYPE,
        RuleOperator.EQUALS,
        "book",
        RuleEffect.INCLUDE,
    )

    evaluator = RuleEvaluator(
        RecommendationRuleConfiguration(
            rules=(rule,)
        )
    )

    result = evaluator.execute(
        resource,
        context,
    )

    assert result.eligible is False


def test_rule_evaluator_applies_score_boost(
    resource,
    context,
):
    rule = make_rule(
        "test.boost",
        RuleType.BOOST,
        RuleField.LANGUAGE,
        RuleOperator.EQUALS,
        "english",
        RuleEffect.ADD_SCORE,
        adjustment=0.1,
    )

    evaluator = RuleEvaluator(
        RecommendationRuleConfiguration(
            rules=(rule,)
        )
    )

    result = evaluator.execute(
        resource,
        context,
        initial_score=0.6,
    )

    assert result.adjusted_score == pytest.approx(0.7)


def test_rule_evaluator_applies_penalty(
    resource,
    context,
):
    rule = make_rule(
        "test.penalty",
        RuleType.PENALTY,
        RuleField.DIFFICULTY,
        RuleOperator.EQUALS,
        "beginner",
        RuleEffect.SUBTRACT_SCORE,
        adjustment=0.1,
    )

    evaluator = RuleEvaluator(
        RecommendationRuleConfiguration(
            rules=(rule,)
        )
    )

    result = evaluator.execute(
        resource,
        context,
        initial_score=0.6,
    )

    assert result.adjusted_score == pytest.approx(0.5)


def test_rule_evaluator_clamps_score_above_one(
    resource,
    context,
):
    rule = make_rule(
        "test.boost",
        RuleType.BOOST,
        RuleField.LANGUAGE,
        RuleOperator.EQUALS,
        "english",
        RuleEffect.ADD_SCORE,
        adjustment=0.2,
    )

    evaluator = RuleEvaluator(
        RecommendationRuleConfiguration(
            rules=(rule,)
        )
    )

    result = evaluator.execute(
        resource,
        context,
        initial_score=0.95,
    )

    assert result.adjusted_score == 1.0


def test_rule_evaluator_clamps_score_below_zero(
    resource,
    context,
):
    rule = make_rule(
        "test.penalty",
        RuleType.PENALTY,
        RuleField.DIFFICULTY,
        RuleOperator.EQUALS,
        "beginner",
        RuleEffect.SUBTRACT_SCORE,
        adjustment=0.5,
    )

    evaluator = RuleEvaluator(
        RecommendationRuleConfiguration(
            rules=(rule,)
        )
    )

    result = evaluator.execute(
        resource,
        context,
        initial_score=0.2,
    )

    assert result.adjusted_score == 0.0


def test_rule_evaluator_ignores_disabled_rules(
    resource,
    context,
):
    rule = make_rule(
        "test.disabled",
        RuleType.PENALTY,
        RuleField.DIFFICULTY,
        RuleOperator.EQUALS,
        "beginner",
        RuleEffect.SUBTRACT_SCORE,
        adjustment=0.5,
    )

    rule = rule.model_copy(
        update={"enabled": False}
    )

    evaluator = RuleEvaluator(
        RecommendationRuleConfiguration(
            rules=(rule,)
        )
    )

    result = evaluator.execute(
        resource,
        context,
        initial_score=0.8,
    )

    assert result.adjusted_score == 0.8


def test_rule_evaluator_rejects_invalid_initial_score(
    resource,
    context,
):
    evaluator = RuleEvaluator(
        RecommendationRuleConfiguration()
    )

    with pytest.raises(ValueError):
        evaluator.execute(
            resource,
            context,
            initial_score=2.0,
        )


def test_rule_evaluator_rejects_boolean_initial_score(
    resource,
    context,
):
    evaluator = RuleEvaluator(
        RecommendationRuleConfiguration()
    )

    with pytest.raises(TypeError):
        evaluator.execute(
            resource,
            context,
            initial_score=True,
        )