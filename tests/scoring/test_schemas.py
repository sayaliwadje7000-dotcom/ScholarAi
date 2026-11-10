import pytest

from app.scoring.schemas import ScoreResult, ScoreComponent


def test_score_result_percentage():
    result = ScoreResult(
        scorer_name="resource",
        score=0.875,
    )

    assert result.percentage == 87.5


def test_score_result_rejects_out_of_range_score():
    with pytest.raises(ValueError):
        ScoreResult(
            scorer_name="resource",
            score=1.5,
        )


def test_score_component():
    component = ScoreComponent(
        name="relevance",
        value=0.8,
        weight=0.5,
        contribution=0.4,
    )

    assert component.contribution == 0.4