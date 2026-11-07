from datetime import datetime, timezone, timedelta

import pytest
from pydantic import ValidationError

from app.schemas.opportunities import (
    OpportunityCreate,
    OpportunityListResponse,
    OpportunityResponse,
    OpportunityStatus,
    OpportunityType,
    OpportunityVerificationStatus,
)


UTC = timezone.utc

NOW = datetime.now(UTC)


def valid_opportunity_data():

    return {
        "provider": "adzuna",
        "external_id": "12345",
        "title": "Software Engineering Internship",
        "description": "An internship for software developers.",
        "opportunity_type": "internship",
        "organizer": "Example Organization",
        "official_url": "https://example.com",
        "source_url": "https://example.com/source",
        "application_url": "https://example.com/apply",
        "eligibility": "Undergraduate students",
        "required_skills": [
            "Python",
            "SQL",
        ],
        "location": "Pune",
        "is_remote": True,
        "registration_start": NOW,
        "registration_deadline": NOW + timedelta(days=30),
        "event_start": NOW + timedelta(days=40),
        "event_end": NOW + timedelta(days=50),
        "status": "open",
        "verification_status": "official_verified",
        "last_verified_at": NOW,
        "retrieved_at": NOW,
        "metadata": {
            "source": "adzuna",
        },
    }


def test_valid_opportunity_creation():

    opportunity = OpportunityCreate(
        **valid_opportunity_data()
    )

    assert opportunity.provider == "adzuna"

    assert opportunity.title == "Software Engineering Internship"

    assert opportunity.opportunity_type == OpportunityType.INTERNSHIP

    assert opportunity.status == OpportunityStatus.OPEN

    assert (
        opportunity.verification_status
        == OpportunityVerificationStatus.OFFICIAL_VERIFIED
    )


def test_default_values():

    opportunity = OpportunityCreate(
        provider="adzuna",
        title="Python Internship",
    )

    assert opportunity.opportunity_type == OpportunityType.OTHER

    assert opportunity.status == OpportunityStatus.DISCOVERED

    assert (
        opportunity.verification_status
        == OpportunityVerificationStatus.UNVERIFIED
    )

    assert opportunity.required_skills == []

    assert opportunity.metadata == {}


def test_empty_provider_rejected():

    data = valid_opportunity_data()

    data["provider"] = " "

    with pytest.raises(ValidationError):
        OpportunityCreate(**data)


def test_empty_title_rejected():

    data = valid_opportunity_data()

    data["title"] = " "

    with pytest.raises(ValidationError):
        OpportunityCreate(**data)


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "ftp://example.com",
        "https://",
        "https://user:password@example.com",
        "not-a-url",
    ],
)
def test_invalid_urls_rejected(url):

    data = valid_opportunity_data()

    data["official_url"] = url

    with pytest.raises(ValidationError):
        OpportunityCreate(**data)


def test_empty_url_becomes_none():

    data = valid_opportunity_data()

    data["official_url"] = ""

    opportunity = OpportunityCreate(**data)

    assert opportunity.official_url is None


def test_naive_datetime_rejected():

    data = valid_opportunity_data()

    data["registration_deadline"] = datetime(
        2026,
        12,
        1,
    )

    with pytest.raises(ValidationError):
        OpportunityCreate(**data)


def test_invalid_registration_dates_rejected():

    data = valid_opportunity_data()

    data["registration_start"] = NOW + timedelta(days=20)

    data["registration_deadline"] = NOW + timedelta(days=10)

    with pytest.raises(ValidationError):
        OpportunityCreate(**data)


def test_invalid_event_dates_rejected():

    data = valid_opportunity_data()

    data["event_start"] = NOW + timedelta(days=60)

    data["event_end"] = NOW + timedelta(days=50)

    with pytest.raises(ValidationError):
        OpportunityCreate(**data)


def test_required_skills_normalization():

    data = valid_opportunity_data()

    data["required_skills"] = [
        "Python",
        " python ",
        "SQL",
        "",
        "Java",
        "JAVA",
    ]

    opportunity = OpportunityCreate(**data)

    assert opportunity.required_skills == [
        "Python",
        "SQL",
        "Java",
    ]


def test_unknown_opportunity_type_rejected():

    data = valid_opportunity_data()

    data["opportunity_type"] = "random_event"

    with pytest.raises(ValidationError):
        OpportunityCreate(**data)


def test_unknown_status_rejected():

    data = valid_opportunity_data()

    data["status"] = "available_now"

    with pytest.raises(ValidationError):
        OpportunityCreate(**data)


def test_unknown_verification_status_rejected():

    data = valid_opportunity_data()

    data["verification_status"] = "trusted"

    with pytest.raises(ValidationError):
        OpportunityCreate(**data)


def test_unknown_fields_rejected():

    data = valid_opportunity_data()

    data["random_field"] = "unexpected"

    with pytest.raises(ValidationError):
        OpportunityCreate(**data)


def test_metadata_accepts_empty_dictionary():

    data = valid_opportunity_data()

    data["metadata"] = {}

    opportunity = OpportunityCreate(**data)

    assert opportunity.metadata == {}


def test_metadata_accepts_opportunity_metadata_alias():

    data = valid_opportunity_data()

    data.pop("metadata")

    data["opportunity_metadata"] = {
        "provider_reference": "12345",
    }

    opportunity = OpportunityCreate(**data)

    assert opportunity.metadata == {
        "provider_reference": "12345",
    }


def test_missing_deadline_is_allowed():

    data = valid_opportunity_data()

    data["registration_deadline"] = None

    opportunity = OpportunityCreate(**data)

    assert opportunity.registration_deadline is None


def test_missing_eligibility_is_allowed():

    data = valid_opportunity_data()

    data["eligibility"] = None

    opportunity = OpportunityCreate(**data)

    assert opportunity.eligibility is None


def test_response_schema():

    data = valid_opportunity_data()

    data.update(
        {
            "id": "8a5f8d8e-4c55-4f95-8c2c-6d5b40f2f123",
            "created_at": NOW,
            "updated_at": NOW,
        }
    )

    response = OpportunityResponse(**data)

    assert response.title == "Software Engineering Internship"

    assert response.metadata == {
        "source": "adzuna",
    }


def test_list_response():

    data = valid_opportunity_data()

    data.update(
        {
            "id": "8a5f8d8e-4c55-4f95-8c2c-6d5b40f2f123",
            "created_at": NOW,
            "updated_at": NOW,
        }
    )

    opportunity = OpportunityResponse(**data)

    response = OpportunityListResponse(
        total_results=1,
        opportunities=[opportunity],
    )

    assert response.total_results == 1

    assert len(response.opportunities) == 1


def test_list_response_rejects_invalid_total():

    with pytest.raises(ValidationError):

        OpportunityListResponse(
            total_results=0,
            opportunities=[],
        )

    data = valid_opportunity_data()

    data.update(
        {
            "id": "8a5f8d8e-4c55-4f95-8c2c-6d5b40f2f123",
            "created_at": NOW,
            "updated_at": NOW,
        }
    )

    opportunity = OpportunityResponse(**data)

    with pytest.raises(ValidationError):

        OpportunityListResponse(
            total_results=0,
            opportunities=[opportunity],
        )