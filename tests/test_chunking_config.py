import pytest

from app.core.chunking_config import ChunkingSettings


def test_default_chunking_settings():
    settings = ChunkingSettings()

    assert settings.chunk_size == 1000
    assert settings.chunk_overlap == 150
    assert settings.minimum_chunk_size == 100
    assert settings.preserve_page_boundaries is True


@pytest.mark.parametrize(
    "kwargs",
    [
        {"chunk_size": 0},
        {"chunk_size": -1},
        {"chunk_overlap": -1},
        {"chunk_size": 100, "chunk_overlap": 100},
        {"chunk_size": 100, "minimum_chunk_size": 101},
        {"minimum_chunk_size": 0},
        {"chunk_size": True},
        {"chunk_overlap": True},
        {"minimum_chunk_size": True},
        {"preserve_page_boundaries": "yes"},
    ],
)
def test_invalid_chunking_settings(kwargs):
    with pytest.raises(ValueError):
        ChunkingSettings(**kwargs)


def test_custom_chunking_settings():
    settings = ChunkingSettings(
        chunk_size=500,
        chunk_overlap=50,
        minimum_chunk_size=40,
        preserve_page_boundaries=False,
    )

    assert settings.chunk_size == 500
    assert settings.chunk_overlap == 50
    assert settings.minimum_chunk_size == 40
    assert settings.preserve_page_boundaries is False