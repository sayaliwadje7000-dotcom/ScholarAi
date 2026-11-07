import pytest

from app.services.opportunities.validity import (
    OpportunityEligibilityEvaluator,
)
from app.services.opportunities.validity.eligibility_evaluator import (
    OpportunityEligibilityEvaluator,
)


def test_missing_student_profile_returns_unknown():
    """
    Missing profile information must not be
    interpreted as confirmed eligibility.
    """
    evaluator = OpportunityEligibilityEvaluator()

    result = evaluator.evaluate(
        eligibility={
            "branches": ["Computer Science"],
            "graduation_years": [2027],
        },
        student_profile={},
    )

    assert result.status == "unknown"
    assert result.unknown_criteria

@pytest.fixture
def evaluator():
    return OpportunityEligibilityEvaluator()


def test_eligible_student(evaluator):

    result = evaluator.evaluate(
        eligibility={
            "branches": ["AIDS", "CSE"],
            "academic_years": [3, 4],
            "required_skills": ["Python", "SQL"],
        },
        student_profile={
            "branch": "AIDS",
            "academic_year": 3,
            "skills": ["Python", "SQL", "Java"],
        },
    )

    assert result.status == "eligible"
    assert result.is_eligible


def test_student_fails_branch_requirement(evaluator):

    result = evaluator.evaluate(
        eligibility={
            "branches": ["CSE"]
        },
        student_profile={
            "branch": "AIDS"
        },
    )

    assert result.status == "not_eligible"
    assert "branches" in result.failed_criteria


def test_missing_student_information_is_unknown(evaluator):

    result = evaluator.evaluate(
        eligibility={
            "branches": ["CSE"]
        },
        student_profile={},
    )

    assert result.status == "unknown"
    assert "branches" in result.unknown_criteria


def test_required_skills_are_checked(evaluator):

    result = evaluator.evaluate(
        eligibility={
            "required_skills": [
                "Python",
                "Machine Learning",
            ]
        },
        student_profile={
            "skills": ["Python"]
        },
    )

    assert result.status == "not_eligible"
    assert "required_skills" in result.failed_criteria


def test_age_range_passes(evaluator):

    result = evaluator.evaluate(
        eligibility={
            "age_min": 18,
            "age_max": 25,
        },
        student_profile={
            "age": 21
        },
    )

    assert result.status == "eligible"


def test_age_range_fails(evaluator):

    result = evaluator.evaluate(
        eligibility={
            "age_min": 18,
            "age_max": 25,
        },
        student_profile={
            "age": 27
        },
    )

    assert result.status == "not_eligible"


def test_multiple_failed_criteria(evaluator):

    result = evaluator.evaluate(
        eligibility={
            "branches": ["CSE"],
            "countries": ["India"],
        },
        student_profile={
            "branch": "AIDS",
            "country": "USA",
        },
    )

    assert result.status == "not_eligible"
    assert len(result.failed_criteria) == 2


def test_empty_eligibility_is_eligible(evaluator):

    result = evaluator.evaluate(
        eligibility={},
        student_profile={},
    )

    assert result.status == "eligible"


def test_invalid_eligibility_type(evaluator):

    with pytest.raises(ValueError):
        evaluator.evaluate(
            eligibility="CSE",
            student_profile={},
        )


def test_invalid_required_skills_type(evaluator):

    with pytest.raises(ValueError):
        evaluator.evaluate(
            eligibility={
                "required_skills": "Python"
            },
            student_profile={
                "skills": ["Python"]
            },
        )


def test_invalid_numeric_profile_value(evaluator):

    with pytest.raises(ValueError):
        evaluator.evaluate(
            eligibility={
                "age_min": 18
            },
            student_profile={
                "age": "twenty"
            },
        )