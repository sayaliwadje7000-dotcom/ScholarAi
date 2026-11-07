import pytest

from app.services.opportunities.ranking import (
    OpportunityRelevanceScorer,
)


@pytest.fixture
def scorer():
    return OpportunityRelevanceScorer()


def test_skills_match(scorer):

    result = scorer.evaluate(
        opportunity={
            "required_skills": ["Python", "SQL"],
        },
        student_profile={
            "skills": ["Python", "SQL", "Java"],
        },
    )

    assert result.skills_score == 100
    assert "skills" in result.matched_signals


def test_partial_skills_match(scorer):

    result = scorer.evaluate(
        opportunity={
            "required_skills": ["Python", "SQL"],
        },
        student_profile={
            "skills": ["Python"],
        },
    )

    assert result.skills_score == 50


def test_opportunity_type_match(scorer):

    result = scorer.evaluate(
        opportunity={
            "opportunity_type": "hackathon",
        },
        student_profile={
            "preferred_opportunity_types": ["hackathon"],
        },
    )

    assert result.opportunity_type_score == 100


def test_interest_match(scorer):

    result = scorer.evaluate(
        opportunity={
            "title": "Artificial Intelligence Competition",
            "description": "Build machine learning applications.",
        },
        student_profile={
            "interests": ["artificial intelligence", "machine learning"],
        },
    )

    assert result.interests_score == 100


def test_location_match(scorer):

    result = scorer.evaluate(
        opportunity={
            "location": "Pune",
            "is_remote": False,
        },
        student_profile={
            "preferred_locations": ["Pune"],
        },
    )

    assert result.location_score == 100


def test_remote_opportunity_matches_location_preference(scorer):

    result = scorer.evaluate(
        opportunity={
            "location": None,
            "is_remote": True,
        },
        student_profile={
            "preferred_locations": ["Pune"],
        },
    )

    assert result.location_score == 100


def test_academic_year_match(scorer):

    result = scorer.evaluate(
        opportunity={
            "eligibility": {
                "academic_years": [3, 4],
            },
        },
        student_profile={
            "academic_year": 3,
        },
    )

    assert result.academic_level_score == 100


def test_query_match(scorer):

    result = scorer.evaluate(
        opportunity={
            "title": "Python Developer Internship",
            "description": "Develop backend applications.",
        },
        query="Python internship",
    )

    assert result.query_score == 100


def test_missing_student_signals_do_not_cause_validation_failure(scorer):

    result = scorer.evaluate(
        opportunity={
            "title": "AI Hackathon",
            "opportunity_type": "hackathon",
            "required_skills": ["Python"],
        },
        student_profile={},
    )

    assert result.score == 0
    assert result.evaluated_weight == 0


def test_missing_skills_are_not_scored_as_zero(scorer):

    result = scorer.evaluate(
        opportunity={
            "required_skills": ["Python"],
            "opportunity_type": "internship",
        },
        student_profile={
            "preferred_opportunity_types": ["internship"],
        },
    )

    assert result.skills_score is None
    assert result.opportunity_type_score == 100


def test_invalid_student_profile(scorer):

    with pytest.raises(Exception):
        scorer.evaluate(
            opportunity={},
            student_profile="invalid",
        )