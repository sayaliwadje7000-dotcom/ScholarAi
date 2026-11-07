from __future__ import annotations

import unicodedata
from collections.abc import Iterable


class ResourceTextNormalizer:
    """Normalize text fields used by educational resources."""

    @staticmethod
    def normalize(value: str | None) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str):
            raise TypeError("Text value must be a string or None.")

        value = unicodedata.normalize("NFKC", value)
        value = value.replace("\u00a0", " ")
        value = " ".join(value.split())
        value = value.strip()

        return value or None

    @staticmethod
    def comparison_key(value: str | None) -> str | None:
        normalized = ResourceTextNormalizer.normalize(value)

        if normalized is None:
            return None

        return normalized.casefold()

    @staticmethod
    def normalize_authors(
        authors: Iterable[str],
    ) -> tuple[str, ...]:
        if isinstance(authors, (str, bytes)):
            raise TypeError("Authors must be an iterable of strings.")

        normalized_authors: list[str] = []
        seen: set[str] = set()

        for author in authors:
            normalized = ResourceTextNormalizer.normalize(author)

            if normalized is None:
                continue

            key = normalized.casefold()

            if key not in seen:
                seen.add(key)
                normalized_authors.append(normalized)

        return tuple(normalized_authors)