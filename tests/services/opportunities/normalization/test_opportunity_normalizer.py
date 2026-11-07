import pytest

from app.services.opportunities.normalization.opportunity_normalizer import (
    OpportunityNormalizer,
)


def make_opportunity(**overrides):

    data = {
        "provider": " ADZUNA ",
        "external_id": "123",
        "title": " Python Internship ",
        "opportunity_type": "INTERNSHIP",
        "official_url": "https://www.example.com/job/",
        "source_url": None,
        "application_url": None,
        "organizer": " Example Company ",
        "eligibility": {},
        "required_skills": [
            "Python",
            " python ",
            "SQL",
            "",
        ],
        "metadata": {},
    }

    data.update(overrides)

    return data


def test_normalize_basic_fields():

    result = OpportunityNormalizer.normalize(
        make_opportunity()
    )

    assert result["provider"] == "adzuna"

    assert result["title"] == "Python Internship"

    assert result["opportunity_type"] == "internship"


def test_normalize_url():

    result = OpportunityNormalizer.normalize(
        make_opportunity()
    )

    assert result["official_url"] == (
        "https://example.com/job"
    )


def test_normalize_required_skills():

    result = OpportunityNormalizer.normalize(
        make_opportunity()
    )

    assert result["required_skills"] == [
        "Python",
        "SQL",
    ]


def test_normalize_preserves_eligibility():

    result = OpportunityNormalizer.normalize(
        make_opportunity(
            eligibility={
                "academic_level": "undergraduate"
            }
        )
    )

    assert result["eligibility"] == {
        "academic_level": "undergraduate"
    }


def test_invalid_provider_rejected():

    with pytest.raises(ValueError):

        OpportunityNormalizer.normalize(
            make_opportunity(provider="")
        )


def test_invalid_eligibility_rejected():

    with pytest.raises(TypeError):

        OpportunityNormalizer.normalize(
            make_opportunity(eligibility="Everyone")
        )


def test_invalid_skills_rejected():

    with pytest.raises(TypeError):

        OpportunityNormalizer.normalize(
            make_opportunity(required_skills="Python")
        )


def test_empty_optional_strings_become_none():

    result = OpportunityNormalizer.normalize(
        make_opportunity(organizer=" ")
    )

    assert result["organizer"] is None