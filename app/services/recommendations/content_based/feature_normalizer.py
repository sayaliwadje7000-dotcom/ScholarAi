from __future__ import annotations

import re
import unicodedata

from collections.abc import Iterable


class ContentFeatureNormalizer:
    """
    Normalizes textual resource features into consistent
    representations suitable for content-based processing.

    Responsibilities:

    1. Unicode normalization.
    2. Whitespace normalization.
    3. Case normalization.
    4. Duplicate removal.
    5. Deterministic tokenization.

    This component does not perform semantic analysis,
    stemming, lemmatization or embedding generation.
    """

    _TOKEN_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)

    @staticmethod
    def normalize_text(value: object) -> str:
        """
        Normalize a single textual value.

        Returns an empty string for None or blank values.

        Non-string values are rejected rather than silently
        converted into misleading textual features.
        """

        if value is None:
            return ""

        if not isinstance(value, str):
            raise TypeError(
                "Content feature values must be strings."
            )

        value = unicodedata.normalize("NFKC", value)

        value = value.strip()

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value.casefold()

    def normalize_terms(
        self,
        values: Iterable[str] | str | None,
    ) -> tuple[str, ...]:
        """
        Normalize a collection of feature values.

        - Accepts a string, iterable of strings or None.
        - Normalizes Unicode and whitespace.
        - Converts values to casefolded form.
        - Removes empty values.
        - Removes duplicate values.
        - Preserves first-occurrence order.

        Returns an immutable tuple.
        """

        if values is None:
            return ()

        if isinstance(values, str):
            values = [values]

        if not isinstance(values, Iterable):
            raise TypeError(
                "Expected a string or iterable of strings."
            )

        normalized: list[str] = []

        seen: set[str] = set()

        for value in values:

            if not isinstance(value, str):
                raise TypeError(
                    "Every content feature must be a string."
                )

            normalized_value = self.normalize_text(value)

            if not normalized_value:
                continue

            if normalized_value in seen:
                continue

            seen.add(normalized_value)

            normalized.append(normalized_value)

        return tuple(normalized)

    def tokenize(
        self,
        values: Iterable[str] | str | None,
    ) -> tuple[str, ...]:
        """
        Convert textual features into deterministic tokens.

        Unicode letters and numbers are retained.

        Punctuation, underscores and whitespace act as
        token boundaries.

        No stop-word removal is performed because terms such
        as 'not', 'without' and 'only' can carry educational
        meaning.
        """

        normalized_values = self.normalize_terms(values)

        tokens: list[str] = []

        seen: set[str] = set()

        for value in normalized_values:

            matches = self._TOKEN_PATTERN.findall(value)

            for token in matches:

                if token in seen:
                    continue

                seen.add(token)

                tokens.append(token)

        return tuple(tokens)