from dataclasses import dataclass


@dataclass(frozen=True)
class StructureSettings:
    """Configuration for document structure extraction."""

    heading_min_font_ratio: float = 1.15

    heading_max_characters: int = 180

    heading_min_confidence: float = 0.55

    detect_tables: bool = True

    detect_lists: bool = True

    preserve_page_layout: bool = True

    def __post_init__(self):

        if self.heading_min_font_ratio < 1.0:
            raise ValueError(
                "Heading font ratio must be at least 1.0."
            )

        if self.heading_max_characters < 10:
            raise ValueError(
                "Heading maximum characters must be at least 10."
            )

        if not 0 <= self.heading_min_confidence <= 1:
            raise ValueError(
                "Heading confidence must be between 0 and 1."
            )