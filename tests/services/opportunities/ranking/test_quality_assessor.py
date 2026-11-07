import pytest

from app.services.opportunities.ranking import (
    OpportunityQualityAssessor,
)

from app.services.opportunities.ranking.exceptions import (
    OpportunityQualityError,
)


@pytest.fixture
def assessor():
    return OpportunityQualityAssessor()


def test_complete_opportunity_has_high_quality(assessor):

    opportunity = {
        "title": "AI Hackathon",
        "description": (
            "A national AI and machine learning hackathon for students. "
            * 5
        ),
        "official_url": "https://example.com/hackathon",
        "organizer": "Example University",
        "registration_start": None,
        "registration_deadline": None,
        "eligibility": {
            "branches": ["CSE", "AIDS"]
        },
        "required_skills": [
            "Python",
            "Machine Learning",
        ],
        "source_url": "https://example.com/source",
        "provider": "example",
        "external_id": "123",
        "opportunity_metadata": {
            "sources": ["example"]
        },
    }

    result = assessor.evaluate(opportunity)

    assert result.score > 80
    assert result.description_score == 100
    assert result.official_url_score == 100
    assert result.organizer_score == 100


def test_missing_description_reduces_quality(assessor):

    result = assessor.evaluate({
        "description": None,
    })

    assert result.description_score == 0
    assert result.score < 100


def test_invalid_official_url_scores_zero(assessor):

    result = assessor.evaluate({
        "official_url": "javascript:alert(1)",
    })

    assert result.official_url_score == 0


def test_missing_provenance_scores_zero(assessor):

    result = assessor.evaluate({
        "description": "A useful opportunity description.",
    })

    assert result.provenance_score == 0


def test_missing_deadline_scores_zero(assessor):

    result = assessor.evaluate({
        "registration_start": None,
        "registration_deadline": None,
    })

    assert result.deadline_score == 0


def test_registration_start_without_deadline_scores_partially(assessor):

    result = assessor.evaluate({
        "registration_start": "2026-11-01",
    })

    assert result.deadline_score == 50


def test_invalid_eligibility_type_is_rejected(assessor):

    with pytest.raises(OpportunityQualityError):
        assessor.evaluate({
            "eligibility": "CSE",
        })


def test_invalid_skills_type_is_rejected(assessor):

    with pytest.raises(OpportunityQualityError):
        assessor.evaluate({
            "required_skills": "Python",
        })


def test_invalid_description_type_is_rejected(assessor):

    with pytest.raises(OpportunityQualityError):
        assessor.evaluate({
            "description": 123,
        })


def test_non_dictionary_opportunity_is_rejected(assessor):

    with pytest.raises(OpportunityQualityError):
        assessor.evaluate("AI Hackathon")