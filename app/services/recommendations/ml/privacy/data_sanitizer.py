"""Metadata sanitization for ScholarAI ML."""

from __future__ import annotations

import re
from typing import Any

from app.services.recommendations.ml.privacy.privacy_config import (
    PrivacyConfig,
)

from app.services.recommendations.ml.privacy.privacy_exceptions import (
    MetadataSanitizationError,
)


class MetadataSanitizer:
    """Remove common PII and sensitive values from metadata."""

    REDACTED = "[REDACTED]"

    SENSITIVE_KEYS = {
        "password",
        "passwd",
        "secret",
        "api_key",
        "apikey",
        "access_token",
        "refresh_token",
        "authorization",
        "cookie",
        "session",
        "private_key",
        "client_secret",
        "email",
        "phone",
        "mobile",
        "address",
        "ip_address",
        "date_of_birth",
        "dob",
        "user_id",
        "resource_id",
        "document_id",
    }

    EMAIL_PATTERN = re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    )

    PHONE_PATTERN = re.compile(
        r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)"
    )

    IPV4_PATTERN = re.compile(
        r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
    )

    BEARER_PATTERN = re.compile(
        r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"
    )

    SECRET_PATTERN = re.compile(
        r"(?i)\b(?:api[_-]?key|access[_-]?token|"
        r"client[_-]?secret|password)\s*[:=]\s*"
        r"[^\s,;]+"
    )

    def __init__(
        self,
        config: PrivacyConfig | None = None,
    ) -> None:

        self.config = config or PrivacyConfig()

    @staticmethod
    def _normalize_key(key: Any) -> str:

        return str(key).strip().casefold()

    def _sanitize_string(
        self,
        value: str,
    ) -> str:

        result = value

        result = self.BEARER_PATTERN.sub(
            self.REDACTED,
            result,
        )

        result = self.SECRET_PATTERN.sub(
            self.REDACTED,
            result,
        )

        result = self.EMAIL_PATTERN.sub(
            self.REDACTED,
            result,
        )

        result = self.IPV4_PATTERN.sub(
            self.REDACTED,
            result,
        )

        result = self.PHONE_PATTERN.sub(
            self.REDACTED,
            result,
        )

        maximum = self.config.maximum_metadata_string_length

        if len(result) > maximum:

            result = result[:maximum] + "...[TRUNCATED]"

        return result

    def sanitize(
        self,
        value: Any,
    ) -> Any:
        """Recursively sanitize supported metadata structures."""

        if not self.config.redact_pii_from_metadata:

            return value

        try:

            return self._sanitize_value(
                value,
                depth=0,
            )

        except MetadataSanitizationError:

            raise

        except Exception as exc:

            raise MetadataSanitizationError(
                "Unable to sanitize metadata."
            ) from exc

    def _sanitize_value(
        self,
        value: Any,
        depth: int,
    ) -> Any:

        if depth > 20:

            raise MetadataSanitizationError(
                "Metadata nesting exceeds the permitted depth."
            )

        if value is None:

            return None

        if isinstance(value, str):

            return self._sanitize_string(value)

        if isinstance(value, bool):

            return value

        if isinstance(value, (int, float)):

            return value

        if isinstance(value, dict):

            sanitized = {}

            for key, item in value.items():

                normalized_key = self._normalize_key(key)

                if normalized_key in self.SENSITIVE_KEYS:

                    sanitized[str(key)] = self.REDACTED

                    continue

                sanitized[str(key)] = self._sanitize_value(
                    item,
                    depth + 1,
                )

            return sanitized

        if isinstance(value, (list, tuple)):

            return [
                self._sanitize_value(
                    item,
                    depth + 1,
                )
                for item in value
            ]

        raise MetadataSanitizationError(
            f"Unsupported metadata type: {type(value).__name__}"
        )