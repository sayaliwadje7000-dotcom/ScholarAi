import pytest

from app.services.opportunities.normalization.text_normalizer import (
    OpportunityTextNormalizer,
)


def test_normalize_text():

    assert OpportunityTextNormalizer.normalize(
        "  AI & Machine Learning  "
    ) == "ai machine learning"


def test_normalize_unicode():

    assert OpportunityTextNormalizer.normalize(
        "ＣＯＤＩＮＧ"
    ) == "coding"


def test_normalize_none():

    assert OpportunityTextNormalizer.normalize(None) == ""


def test_normalize_rejects_non_string():

    with pytest.raises(TypeError):

        OpportunityTextNormalizer.normalize(123)


def test_normalize_title():

    assert OpportunityTextNormalizer.normalize_title(
        " National Hackathon "
    ) == "national hackathon"


def test_normalize_identifier():

    assert OpportunityTextNormalizer.normalize_identifier(
        "Provider 123"
    ) == "provider123"