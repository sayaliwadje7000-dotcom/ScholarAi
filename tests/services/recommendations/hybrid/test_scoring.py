from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.services.recommendations.hybrid.contracts import (
    ComponentScore,
    ComponentStatus,
    HybridCandidate,
    RecommendationComponent,
    RecommendationProvenance,
    ScoreDirection,
)

from app.services.recommendations.hybrid.scoring import (
    HybridScoreNormalizer,
    HybridScoringPipeline,
    HybridWeightConfig,
    HybridWeightingEngine,
    OutOfRangePolicy,
    ScoreNormalizationConfig,
    ScoreNormalizationError,
    WeightConfigurationError,
    HybridAggregationError,
)


@pytest.fixture
def timestamp():
    return datetime.now(timezone.utc)


@pytest.fixture
def normalization_configs():
    return {
        RecommendationComponent.RULE_BASED:
            ScoreNormalizationConfig(0.0, 1.0),

        RecommendationComponent.CONTENT_BASED:
            ScoreNormalizationConfig(0.0, 1.0),

        RecommendationComponent.MACHINE_LEARNING:
            ScoreNormalizationConfig(0.0, 1.0),
    }


@pytest.fixture
def normalizer(normalization_configs):
    return HybridScoreNormalizer(
        configurations=normalization_configs,
    )


@pytest.fixture
def weighting_engine():
    return HybridWeightingEngine(
        HybridWeightConfig(
            weights={
                RecommendationComponent.RULE_BASED: 0.30,
                RecommendationComponent.CONTENT_BASED: 0.30,
                RecommendationComponent.MACHINE_LEARNING: 0.40,
            }
        )
    )


@pytest.fixture
def pipeline(normalizer, weighting_engine):
    return HybridScoringPipeline(
        normalizer=normalizer,
        weighting_engine=weighting_engine,
    )


@pytest.fixture
def provenance(timestamp):
    return RecommendationProvenance(
        component=RecommendationComponent.RULE_BASED,
        source_name="rule_engine",
        retrieved_at=timestamp,
    )


def make_score(
    component,
    value,
    timestamp,
    status=ComponentStatus.AVAILABLE,
):
    return ComponentScore(
        component=component,
        status=status,
        value=value,
        calculated_at=timestamp,
    )


def make_candidate(
    scores,
    provenance,
    timestamp,
):
    return HybridCandidate(
        resource_id=uuid4(),
        title="Machine Learning Course",
        resource_type="course",
        component_scores=tuple(scores),
        provenance=(provenance,),
        discovered_at=timestamp,
    )


def test_min_max_normalization(normalizer, timestamp):
    score = make_score(
        RecommendationComponent.RULE_BASED,
        0.75,
        timestamp,
    )

    result = normalizer.normalize(score)

    assert result.normalized_score == pytest.approx(0.75)

    assert result.raw_score == 0.75


def test_normalization_minimum_becomes_zero(normalizer, timestamp):
    score = make_score(
        RecommendationComponent.RULE_BASED,
        0.0,
        timestamp,
    )

    result = normalizer.normalize(score)

    assert result.normalized_score == 0.0


def test_normalization_maximum_becomes_one(normalizer, timestamp):
    score = make_score(
        RecommendationComponent.RULE_BASED,
        1.0,
        timestamp,
    )

    result = normalizer.normalize(score)

    assert result.normalized_score == 1.0


def test_normalization_supports_negative_raw_scores(timestamp):
    normalizer = HybridScoreNormalizer(
        {
            RecommendationComponent.CONTENT_BASED:
                ScoreNormalizationConfig(-1.0, 1.0),
        }
    )

    score = make_score(
        RecommendationComponent.CONTENT_BASED,
        -0.5,
        timestamp,
    )

    result = normalizer.normalize(score)

    assert result.normalized_score == pytest.approx(0.25)


def test_lower_is_better_score_is_inverted(timestamp):
    normalizer = HybridScoreNormalizer(
        {
            RecommendationComponent.RULE_BASED:
                ScoreNormalizationConfig(0.0, 100.0),
        }
    )

    score = ComponentScore(
        component=RecommendationComponent.RULE_BASED,
        status=ComponentStatus.AVAILABLE,
        value=25.0,
        direction=ScoreDirection.LOWER_IS_BETTER,
        calculated_at=timestamp,
    )

    result = normalizer.normalize(score)

    assert result.normalized_score == pytest.approx(0.75)


def test_out_of_range_score_is_rejected(normalizer, timestamp):
    score = make_score(
        RecommendationComponent.RULE_BASED,
        1.5,
        timestamp,
    )

    with pytest.raises(ScoreNormalizationError):
        normalizer.normalize(score)


def test_out_of_range_score_can_be_clamped(timestamp):
    normalizer = HybridScoreNormalizer(
        {
            RecommendationComponent.RULE_BASED:
                ScoreNormalizationConfig(
                    minimum=0.0,
                    maximum=1.0,
                    out_of_range_policy=OutOfRangePolicy.CLAMP,
                ),
        }
    )

    score = make_score(
        RecommendationComponent.RULE_BASED,
        1.5,
        timestamp,
    )

    result = normalizer.normalize(score)

    assert result.normalized_score == 1.0

    assert result.raw_score == 1.5

    assert result.was_clamped is True


def test_normalizer_rejects_unavailable_score(
    normalizer,
    timestamp,
):
    score = make_score(
        RecommendationComponent.MACHINE_LEARNING,
        None,
        timestamp,
        ComponentStatus.UNAVAILABLE,
    )

    with pytest.raises(ScoreNormalizationError):
        normalizer.normalize(score)


def test_normalizer_rejects_missing_configuration(timestamp):
    normalizer = HybridScoreNormalizer(
        {
            RecommendationComponent.RULE_BASED:
                ScoreNormalizationConfig(0.0, 1.0),
        }
    )

    score = make_score(
        RecommendationComponent.MACHINE_LEARNING,
        0.7,
        timestamp,
    )

    with pytest.raises(ScoreNormalizationError):
        normalizer.normalize(score)


def test_normalization_configuration_rejects_invalid_bounds():
    with pytest.raises(ScoreNormalizationError):
        ScoreNormalizationConfig(
            minimum=1.0,
            maximum=1.0,
        )


def test_weight_configuration_rejects_negative_weight():
    with pytest.raises(WeightConfigurationError):
        HybridWeightConfig(
            weights={
                RecommendationComponent.RULE_BASED: -0.1,
            }
        )


def test_weight_configuration_rejects_all_zero_weights():
    with pytest.raises(WeightConfigurationError):
        HybridWeightConfig(
            weights={
                RecommendationComponent.RULE_BASED: 0.0,
                RecommendationComponent.CONTENT_BASED: 0.0,
            }
        )


def test_weight_configuration_rejects_invalid_component():
    with pytest.raises(WeightConfigurationError):
        HybridWeightConfig(
            weights={
                "rule_based": 1.0,
            }
        )


def test_weight_configuration_rejects_boolean_weight():
    with pytest.raises(WeightConfigurationError):
        HybridWeightConfig(
            weights={
                RecommendationComponent.RULE_BASED: True,
            }
        )


def test_weight_configuration_is_immutable():
    weights = {
        RecommendationComponent.RULE_BASED: 0.5,
        RecommendationComponent.CONTENT_BASED: 0.5,
    }

    configuration = HybridWeightConfig(weights=weights)

    weights[RecommendationComponent.RULE_BASED] = 0.0

    assert configuration.weights[
        RecommendationComponent.RULE_BASED
    ] == 0.5


def test_weighting_engine_combines_all_three_components(
    pipeline,
    provenance,
    timestamp,
):
    candidate = make_candidate(
        [
            make_score(
                RecommendationComponent.RULE_BASED,
                0.8,
                timestamp,
            ),
            make_score(
                RecommendationComponent.CONTENT_BASED,
                0.9,
                timestamp,
            ),
            make_score(
                RecommendationComponent.MACHINE_LEARNING,
                0.7,
                timestamp,
            ),
        ],
        provenance,
        timestamp,
    )

    result = pipeline.score(candidate)

    expected = (
        0.8 * 0.30
        + 0.9 * 0.30
        + 0.7 * 0.40
    )

    assert result.hybrid_score == pytest.approx(expected)


def test_weighting_engine_renormalizes_when_ml_is_unavailable(
    pipeline,
    provenance,
    timestamp,
):
    candidate = make_candidate(
        [
            make_score(
                RecommendationComponent.RULE_BASED,
                0.8,
                timestamp,
            ),
            make_score(
                RecommendationComponent.CONTENT_BASED,
                0.6,
                timestamp,
            ),
            make_score(
                RecommendationComponent.MACHINE_LEARNING,
                None,
                timestamp,
                ComponentStatus.UNAVAILABLE,
            ),
        ],
        provenance,
        timestamp,
    )

    result = pipeline.score(candidate)

    expected = (
        0.8 * 0.5
        + 0.6 * 0.5
    )

    assert result.hybrid_score == pytest.approx(expected)

    assert result.effective_weight_total == pytest.approx(1.0)

    assert RecommendationComponent.MACHINE_LEARNING in (
        result.excluded_components
    )


def test_actual_zero_score_is_not_treated_as_missing(
    pipeline,
    provenance,
    timestamp,
):
    candidate = make_candidate(
        [
            make_score(
                RecommendationComponent.RULE_BASED,
                0.0,
                timestamp,
            ),
            make_score(
                RecommendationComponent.CONTENT_BASED,
                1.0,
                timestamp,
            ),
        ],
        provenance,
        timestamp,
    )

    result = pipeline.score(candidate)

    expected = (
        0.0 * 0.5
        + 1.0 * 0.5
    )

    assert result.hybrid_score == pytest.approx(expected)

    assert RecommendationComponent.RULE_BASED in (
        result.available_components
    )


def test_failed_component_is_excluded(
    pipeline,
    provenance,
    timestamp,
):
    candidate = make_candidate(
        [
            make_score(
                RecommendationComponent.RULE_BASED,
                0.8,
                timestamp,
            ),
            make_score(
                RecommendationComponent.CONTENT_BASED,
                None,
                timestamp,
                ComponentStatus.FAILED,
            ),
        ],
        provenance,
        timestamp,
    )

    result = pipeline.score(candidate)

    assert result.hybrid_score == pytest.approx(0.8)

    assert RecommendationComponent.CONTENT_BASED in (
        result.excluded_components
    )


def test_zero_weight_component_is_excluded(timestamp, provenance):
    normalizer = HybridScoreNormalizer(
        {
            RecommendationComponent.RULE_BASED:
                ScoreNormalizationConfig(0.0, 1.0),

            RecommendationComponent.CONTENT_BASED:
                ScoreNormalizationConfig(0.0, 1.0),
        }
    )

    engine = HybridWeightingEngine(
        HybridWeightConfig(
            weights={
                RecommendationComponent.RULE_BASED: 1.0,
                RecommendationComponent.CONTENT_BASED: 0.0,
            }
        )
    )

    pipeline = HybridScoringPipeline(
        normalizer,
        engine,
    )

    candidate = make_candidate(
        [
            make_score(
                RecommendationComponent.RULE_BASED,
                0.7,
                timestamp,
            ),
            make_score(
                RecommendationComponent.CONTENT_BASED,
                0.9,
                timestamp,
            ),
        ],
        provenance,
        timestamp,
    )

    result = pipeline.score(candidate)

    assert result.hybrid_score == pytest.approx(0.7)

    assert RecommendationComponent.CONTENT_BASED in (
        result.excluded_components
    )


def test_no_available_positive_weight_component_fails(
    pipeline,
    provenance,
    timestamp,
):
    candidate = make_candidate(
        [
            make_score(
                RecommendationComponent.MACHINE_LEARNING,
                None,
                timestamp,
                ComponentStatus.UNAVAILABLE,
            ),
        ],
        provenance,
        timestamp,
    )

    with pytest.raises(HybridAggregationError):
        pipeline.score(candidate)


def test_aggregation_rejects_duplicate_normalized_components(
    pipeline,
    provenance,
    timestamp,
):
    candidate = make_candidate(
        [
            make_score(
                RecommendationComponent.RULE_BASED,
                0.8,
                timestamp,
            ),
        ],
        provenance,
        timestamp,
    )

    normalized = pipeline._normalizer.normalize(
        candidate.component_scores[0]
    )

    with pytest.raises(HybridAggregationError):
        pipeline._weighting_engine.aggregate(
            candidate,
            (normalized, normalized),
        )


def test_result_preserves_component_contributions(
    pipeline,
    provenance,
    timestamp,
):
    candidate = make_candidate(
        [
            make_score(
                RecommendationComponent.RULE_BASED,
                0.8,
                timestamp,
            ),
            make_score(
                RecommendationComponent.CONTENT_BASED,
                0.6,
                timestamp,
            ),
        ],
        provenance,
        timestamp,
    )

    result = pipeline.score(candidate)

    assert len(result.contributions) == 2

    assert sum(
        contribution.effective_weight
        for contribution in result.contributions
    ) == pytest.approx(1.0)

    assert result.hybrid_score == pytest.approx(
        sum(
            contribution.weighted_contribution
            for contribution in result.contributions
        )
    )


def test_hybrid_score_is_deterministic(
    pipeline,
    provenance,
    timestamp,
):
    candidate = make_candidate(
        [
            make_score(
                RecommendationComponent.RULE_BASED,
                0.7,
                timestamp,
            ),
            make_score(
                RecommendationComponent.CONTENT_BASED,
                0.8,
                timestamp,
            ),
            make_score(
                RecommendationComponent.MACHINE_LEARNING,
                0.9,
                timestamp,
            ),
        ],
        provenance,
        timestamp,
    )

    first = pipeline.score(candidate)

    second = pipeline.score(candidate)

    assert first.hybrid_score == second.hybrid_score


def test_hybrid_score_stays_between_zero_and_one(
    pipeline,
    provenance,
    timestamp,
):
    candidate = make_candidate(
        [
            make_score(
                RecommendationComponent.RULE_BASED,
                0.0,
                timestamp,
            ),
            make_score(
                RecommendationComponent.CONTENT_BASED,
                1.0,
                timestamp,
            ),
            make_score(
                RecommendationComponent.MACHINE_LEARNING,
                0.5,
                timestamp,
            ),
        ],
        provenance,
        timestamp,
    )

    result = pipeline.score(candidate)

    assert 0.0 <= result.hybrid_score <= 1.0