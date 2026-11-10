import pytest

from app.scoring.integrations import create_scoring_engine
from app.scoring.exceptions import ScorerNotFoundError


def test_scoring_engine_registers_all_scorers():
    engine = create_scoring_engine()

    names = engine.registry.list_scorers()

    assert "resource" in names
    assert "search" in names
    assert "rag" in names
    assert "opportunity" in names
    assert "answer" in names
    assert "personalization" in names


def test_resource_scoring():
    engine = create_scoring_engine()

    result = engine.score(
        "resource",
        {
            "query_relevance": 0.9,
            "subject_match": 0.8,
            "quality": 0.9,
            "freshness": 0.7,
            "difficulty_match": 0.8,
        },
    )

    assert result.scorer_name == "resource"
    assert result.score == pytest.approx(0.845)
    assert result.percentage == 84.5


def test_opportunity_scoring():
    engine = create_scoring_engine()

    result = engine.score(
        "opportunity",
        {
            "skill_match": 0.9,
            "interest_match": 0.8,
            "eligibility_match": 1.0,
            "deadline_feasibility": 0.7,
            "opportunity_quality": 0.9,
        },
    )

    assert result.score == pytest.approx(0.88)


def test_unknown_scorer_raises_error():
    engine = create_scoring_engine()

    with pytest.raises(ScorerNotFoundError):
        engine.score("unknown", {})