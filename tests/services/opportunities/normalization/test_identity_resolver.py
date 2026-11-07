import pytest

from app.services.opportunities.normalization.identity_resolver import (
    OpportunityIdentityResolver,
)


def make_opportunity(**overrides):

    data = {
        "provider": "provider_a",
        "external_id": "123",
        "title": "AI Hackathon",
        "organizer": "Example University",
        "opportunity_type": "hackathon",
        "official_url": "https://example.com/event",
        "event_start": None,
    }

    data.update(overrides)

    return data


def test_same_canonical_url_produces_same_identity():

    first = make_opportunity(
        official_url="https://www.example.com/event?utm_source=a"
    )

    second = make_opportunity(
        provider="provider_b",
        external_id="456",
        official_url="https://example.com/event",
    )

    assert (
        OpportunityIdentityResolver.resolve(first)
        ==
        OpportunityIdentityResolver.resolve(second)
    )


def test_provider_identity_fallback():

    first = make_opportunity(
        official_url=None,
    )

    second = make_opportunity(
        official_url=None,
    )

    assert (
        OpportunityIdentityResolver.resolve(first)
        ==
        OpportunityIdentityResolver.resolve(second)
    )


def test_different_provider_ids_produce_different_identity():

    first = make_opportunity(
        official_url=None,
        provider="provider_a",
        external_id="123",
    )

    second = make_opportunity(
        official_url=None,
        provider="provider_b",
        external_id="456",
    )

    assert (
        OpportunityIdentityResolver.resolve(first)
        !=
        OpportunityIdentityResolver.resolve(second)
    )


def test_semantic_identity():

    first = make_opportunity(
        official_url=None,
        external_id=None,
    )

    second = make_opportunity(
        official_url=None,
        external_id=None,
        title=" AI Hackathon ",
    )

    assert (
        OpportunityIdentityResolver.resolve(first)
        ==
        OpportunityIdentityResolver.resolve(second)
    )


def test_different_organizers_produce_different_identity():

    first = make_opportunity(
        official_url=None,
        external_id=None,
        organizer="University A",
    )

    second = make_opportunity(
        official_url=None,
        external_id=None,
        organizer="University B",
    )

    assert (
        OpportunityIdentityResolver.resolve(first)
        !=
        OpportunityIdentityResolver.resolve(second)
    )


def test_missing_title_rejected():

    data = make_opportunity(
        official_url=None,
        external_id=None,
        title="",
    )

    with pytest.raises(ValueError):

        OpportunityIdentityResolver.resolve(data)


def test_missing_organizer_rejected():

    data = make_opportunity(
        official_url=None,
        external_id=None,
        organizer=None,
    )

    with pytest.raises(ValueError):

        OpportunityIdentityResolver.resolve(data)