import pytest

from app.services.educational_resources.normalization.text_normalizer import (
    ResourceTextNormalizer,
)


def test_normalize_collapses_whitespace():
    result = ResourceTextNormalizer.normalize(
        "  Artificial   Intelligence   "
    )

    assert result == "Artificial Intelligence"


def test_normalize_unicode():
    result = ResourceTextNormalizer.normalize(
        "ＡＩ　Research"
    )

    assert result == "AI Research"


def test_normalize_none():
    assert ResourceTextNormalizer.normalize(None) is None


def test_normalize_empty_string():
    assert ResourceTextNormalizer.normalize("   ") is None


def test_comparison_key_is_case_insensitive():
    assert (
        ResourceTextNormalizer.comparison_key("Machine Learning")
        ==
        ResourceTextNormalizer.comparison_key("MACHINE LEARNING")
    )


def test_normalize_authors_removes_duplicates():
    result = ResourceTextNormalizer.normalize_authors(
        (
            "John Smith",
            "  Jane Doe ",
            "john smith",
            "Jane Doe",
        )
    )

    assert result == (
        "John Smith",
        "Jane Doe",
    )


def test_normalize_authors_rejects_string():
    with pytest.raises(TypeError):
        ResourceTextNormalizer.normalize_authors("John Smith")


def test_normalize_rejects_invalid_type():
    with pytest.raises(TypeError):
        ResourceTextNormalizer.normalize(123)