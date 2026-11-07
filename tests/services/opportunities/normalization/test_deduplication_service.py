from app.services.opportunities.normalization.deduplication_service import (
    OpportunityDeduplicationService,
)


def make_opportunity(**overrides):

    data = {
        "provider": "provider_a",
        "external_id": "123",
        "title": "National AI Hackathon",
        "opportunity_type": "hackathon",
        "organizer": "Example University",
        "official_url": "https://example.com/hackathon",
        "source_url": "https://provider-a.com/listing",
        "application_url": "https://example.com/register",
        "description": "Build AI solutions.",
        "eligibility": {
            "academic_level": "undergraduate"
        },
        "required_skills": [
            "Python",
        ],
        "metadata": {},
    }

    data.update(overrides)

    return data


def test_deduplicate_same_opportunity():

    first = make_opportunity()

    second = make_opportunity(
        provider="provider_b",
        external_id="456",
        source_url="https://provider-b.com/listing",
    )

    result = OpportunityDeduplicationService.deduplicate(
        [first, second]
    )

    assert len(result) == 1


def test_preserve_all_provider_sources():

    first = make_opportunity()

    second = make_opportunity(
        provider="provider_b",
        external_id="456",
    )

    result = OpportunityDeduplicationService.deduplicate(
        [first, second]
    )

    sources = result[0]["metadata"]["sources"]

    providers = {
        source["provider"]
        for source in sources
    }

    assert providers == {
        "provider_a",
        "provider_b",
    }


def test_merge_required_skills():

    first = make_opportunity(
        required_skills=["Python"]
    )

    second = make_opportunity(
        provider="provider_b",
        external_id="456",
        required_skills=["Python", "SQL"],
    )

    result = OpportunityDeduplicationService.deduplicate(
        [first, second]
    )

    assert result[0]["required_skills"] == [
        "Python",
        "SQL",
    ]


def test_do_not_merge_different_official_urls():

    first = make_opportunity(
        official_url="https://example.com/event-a"
    )

    second = make_opportunity(
        official_url="https://example.com/event-b"
    )

    result = OpportunityDeduplicationService.deduplicate(
        [first, second]
    )

    assert len(result) == 2


def test_empty_input():

    result = OpportunityDeduplicationService.deduplicate([])

    assert result == []


def test_invalid_input():

    try:

        OpportunityDeduplicationService.deduplicate(
            "not a list"
        )

        assert False

    except TypeError:

        assert True


def test_eligibility_conflicts_are_preserved():

    first = make_opportunity(
        eligibility={
            "academic_level": "undergraduate"
        }
    )

    second = make_opportunity(
        provider="provider_b",
        external_id="456",
        eligibility={
            "academic_level": "postgraduate"
        },
    )

    result = OpportunityDeduplicationService.deduplicate(
        [first, second]
    )

    conflicts = result[0]["metadata"]["eligibility_conflicts"]

    assert conflicts["academic_level"] == [
        "undergraduate",
        "postgraduate",
    ]


def test_merge_description_when_missing():

    first = make_opportunity(
        description=None
    )

    second = make_opportunity(
        provider="provider_b",
        external_id="456",
        description="Detailed opportunity description.",
    )

    result = OpportunityDeduplicationService.deduplicate(
        [first, second]
    )

    assert result[0]["description"] == (
        "Detailed opportunity description."
    )


def test_preserve_metadata_conflicts():

    first = make_opportunity(
        metadata={
            "duration": "3 months"
        }
    )

    second = make_opportunity(
        provider="provider_b",
        external_id="456",
        metadata={
            "duration": "6 months"
        },
    )

    result = OpportunityDeduplicationService.deduplicate(
        [first, second]
    )

    conflicts = result[0]["metadata"]["metadata_conflicts"]

    assert conflicts["duration"] == [
        "3 months",
        "6 months",
    ]
    def test_cross_provider_duplicates_preserve_provenance():

     first = {
        "provider": "provider_a",
        "external_id": "A101",
        "title": "Python AI Hackathon",
        "opportunity_type": "hackathon",
        "official_url": "https://example.com/hackathon",
        "metadata": {},
        "required_skills": ["Python"],
        "eligibility": {},
    }

    second = {
        "provider": "provider_b",
        "external_id": "B201",
        "title": "Python AI Hackathon 2027",
        "opportunity_type": "hackathon",
        "official_url": "https://example.com/hackathon",
        "metadata": {},
        "required_skills": ["Machine Learning"],
        "eligibility": {},
    }

    result = OpportunityDeduplicationService.deduplicate(
        [first, second]
    )

    assert len(result) == 1

    assert set(
        item["provider"]
        for item in result[0]["metadata"]["sources"]
    ) == {
        "provider_a",
        "provider_b",
    }

    assert "Python" in result[0]["required_skills"]

    assert "Machine Learning" in result[0]["required_skills"]