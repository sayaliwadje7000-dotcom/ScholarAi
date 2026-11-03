import pytest

from app.core.structure_config import StructureSettings


def test_default_settings():

    settings = StructureSettings()

    assert settings.heading_min_font_ratio == 1.15

    assert settings.heading_max_characters == 180

    assert settings.detect_tables is True

    assert settings.detect_lists is True


def test_invalid_heading_font_ratio():

    with pytest.raises(ValueError):

        StructureSettings(
            heading_min_font_ratio=0.5
        )


def test_invalid_heading_max_characters():

    with pytest.raises(ValueError):

        StructureSettings(
            heading_max_characters=5
        )


def test_invalid_heading_confidence():

    with pytest.raises(ValueError):

        StructureSettings(
            heading_min_confidence=1.5
        )


def test_valid_custom_settings():

    settings = StructureSettings(
        heading_min_font_ratio=1.3,
        heading_max_characters=150,
        heading_min_confidence=0.7,
        detect_tables=False,
    )

    assert settings.heading_min_font_ratio == 1.3

    assert settings.detect_tables is False