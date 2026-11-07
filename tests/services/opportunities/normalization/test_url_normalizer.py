import pytest

from app.services.opportunities.normalization.url_normalizer import (
    OpportunityURLNormalizer,
)


def test_remove_tracking_parameters():

    result = OpportunityURLNormalizer.normalize(
        "https://www.example.com/event/?utm_source=google&fbclid=123"
    )

    assert result == "https://example.com/event"


def test_remove_default_https_port():

    result = OpportunityURLNormalizer.normalize(
        "https://example.com:443/event"
    )

    assert result == "https://example.com/event"


def test_preserve_meaningful_query_parameters():

    result = OpportunityURLNormalizer.normalize(
        "https://example.com/search?category=hackathon"
    )

    assert result == (
        "https://example.com/search?category=hackathon"
    )


def test_remove_fragment():

    result = OpportunityURLNormalizer.normalize(
        "https://example.com/event#registration"
    )

    assert result == "https://example.com/event"


def test_invalid_scheme():

    assert OpportunityURLNormalizer.normalize(
        "javascript:alert(1)"
    ) is None


def test_empty_url():

    assert OpportunityURLNormalizer.normalize("") is None


def test_non_string_rejected():

    with pytest.raises(TypeError):

        OpportunityURLNormalizer.normalize(123)
def test_query_parameter_order_does_not_change_identity():

    first = OpportunityURLNormalizer.normalize(
        "https://example.com/event?id=123&source=website"
    )

    second = OpportunityURLNormalizer.normalize(
        "https://example.com/event?source=website&id=123"
    )

    assert first == second        