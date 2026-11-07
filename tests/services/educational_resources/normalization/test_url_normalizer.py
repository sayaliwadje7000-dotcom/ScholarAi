import pytest

from app.services.educational_resources.normalization.url_normalizer import (
    ResourceURLNormalizationError,
    ResourceURLNormalizer,
)


def test_removes_tracking_parameters():
    result = ResourceURLNormalizer.normalize(
        "https://example.com/article"
        "?utm_source=google&fbclid=123"
    )

    assert result == "https://example.com/article"


def test_normalizes_hostname():
    result = ResourceURLNormalizer.normalize(
        "HTTPS://EXAMPLE.COM/Article/"
    )

    assert result == "https://example.com/Article"


def test_removes_default_https_port():
    result = ResourceURLNormalizer.normalize(
        "https://example.com:443/article"
    )

    assert result == "https://example.com/article"


def test_preserves_youtube_video_id():
    result = ResourceURLNormalizer.normalize(
        "https://www.youtube.com/watch?v=abc123&utm_source=test"
    )

    assert result == (
        "https://www.youtube.com/watch?v=abc123"
    )


def test_preserves_google_books_id():
    result = ResourceURLNormalizer.normalize(
        "https://books.google.com/books?id=book123&utm_source=test"
    )

    assert result == (
        "https://books.google.com/books?id=book123"
    )


def test_removes_fragment():
    result = ResourceURLNormalizer.normalize(
        "https://example.com/article#section-1"
    )

    assert result == "https://example.com/article"


def test_normalizes_duplicate_slashes_in_path():
    result = ResourceURLNormalizer.normalize(
        "https://example.com/articles//machine-learning"
    )

    assert result == (
        "https://example.com/articles/machine-learning"
    )


def test_none_url_returns_none():
    assert ResourceURLNormalizer.normalize(None) is None


def test_empty_url_returns_none():
    assert ResourceURLNormalizer.normalize(" ") is None


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/file",
        "javascript:alert(1)",
        "https:///missing-host",
        "https://user:password@example.com",
        "https://example.com:invalid/path",
    ],
)
def test_rejects_invalid_urls(url):
    with pytest.raises(ResourceURLNormalizationError):
        ResourceURLNormalizer.normalize(url)