from dataclasses import dataclass


@dataclass(frozen=True)
class TextCleaningSettings:
    """
    Configuration for document text cleaning.
    """

    normalize_unicode: bool = True

    normalize_ligatures: bool = True

    remove_control_characters: bool = True

    normalize_whitespace: bool = True

    repair_hyphenated_words: bool = True

    remove_repeated_headers: bool = False

    remove_repeated_footers: bool = False

    minimum_repeated_page_ratio: float = 0.6

    minimum_line_length: int = 2

    maximum_consecutive_blank_lines: int = 1

    preserve_page_numbers: bool = True