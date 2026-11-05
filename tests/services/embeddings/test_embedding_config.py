import pytest

from app.core.embedding_config import EmbeddingSettings


def test_default_configuration():
    settings = EmbeddingSettings()

    assert settings.provider == "gemini"
    assert settings.model == "gemini-embedding-2"
    assert settings.dimensions == 1536


@pytest.mark.parametrize(
    "dimension",
    [768, 1536, 3072],
)
def test_supported_dimensions(dimension):
    settings = EmbeddingSettings(
        dimensions=dimension
    )

    assert settings.dimensions == dimension


def test_invalid_dimensions():
    with pytest.raises(ValueError):
        EmbeddingSettings(dimensions=1024)


def test_invalid_timeout():
    with pytest.raises(ValueError):
        EmbeddingSettings(
            request_timeout_seconds=0
        )


def test_invalid_concurrency():
    with pytest.raises(ValueError):
        EmbeddingSettings(
            max_concurrent_requests=0
        )


def test_invalid_retry_count():
    with pytest.raises(ValueError):
        EmbeddingSettings(max_retries=-1)


def test_retry_delay_relationship():
    with pytest.raises(ValueError):
        EmbeddingSettings(
            retry_base_delay_seconds=5,
            retry_max_delay_seconds=2,
        )