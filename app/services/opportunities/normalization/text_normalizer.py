import re
import unicodedata


class OpportunityTextNormalizer:
    """
    Normalizes opportunity text for consistent comparison.

    Operations:
    - Unicode normalization.
    - Case folding.
    - Whitespace normalization.
    - Punctuation normalization.
    """

    @staticmethod
    def normalize(value: str | None) -> str:

        if value is None:
            return ""

        if not isinstance(value, str):
            raise TypeError("Text value must be a string.")

        value = unicodedata.normalize("NFKC", value)

        value = value.casefold()

        value = re.sub(
            r"[^\w\s]",
            " ",
            value,
            flags=re.UNICODE,
        )

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value.strip()

    @classmethod
    def normalize_title(cls, value: str | None) -> str:

        return cls.normalize(value)

    @classmethod
    def normalize_organizer(cls, value: str | None) -> str:

        return cls.normalize(value)

    @classmethod
    def normalize_description(cls, value: str | None) -> str:

        return cls.normalize(value)

    @classmethod
    def normalize_identifier(cls, value: str | None) -> str:

        return cls.normalize(value).replace(" ", "")