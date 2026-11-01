"""
ScholarAI Safety Service.

Responsibilities:
1. Academic scope screening.
2. Prompt injection detection.
3. System instruction protection.
4. Unsafe request screening.
5. Sensitive output detection.
6. Standardized safety responses.
"""

import re

from dataclasses import dataclass
from enum import Enum

from app.core.safety_config import (
    PROMPT_INJECTION_PATTERNS,
    OUT_OF_SCOPE_PATTERNS,
    UNSAFE_REQUEST_PATTERNS,
    PROMPT_INJECTION_RESPONSE,
    OUT_OF_SCOPE_RESPONSE,
    UNSAFE_REQUEST_RESPONSE,
    OUTPUT_SECURITY_RESPONSE,
)


class SafetyCategory(str, Enum):

    SAFE = "safe"

    PROMPT_INJECTION = "prompt_injection"

    OUT_OF_SCOPE = "out_of_scope"

    UNSAFE_REQUEST = "unsafe_request"

    SENSITIVE_OUTPUT = "sensitive_output"


@dataclass(frozen=True)
class SafetyResult:

    allowed: bool

    category: SafetyCategory

    response: str | None = None


def normalize_message(message: str) -> str:

    return " ".join(message.casefold().split())


def contains_pattern(
    message: str,
    patterns: list[str],
) -> bool:

    normalized = normalize_message(message)

    return any(
        pattern in normalized
        for pattern in patterns
    )


# ---------------------------------------------------------
# INPUT CHECKS
# ---------------------------------------------------------

def detect_prompt_injection(message: str) -> bool:

    return contains_pattern(
        message,
        PROMPT_INJECTION_PATTERNS,
    )


def detect_out_of_scope_request(message: str) -> bool:

    return contains_pattern(
        message,
        OUT_OF_SCOPE_PATTERNS,
    )


def detect_unsafe_request(message: str) -> bool:

    return contains_pattern(
        message,
        UNSAFE_REQUEST_PATTERNS,
    )


def evaluate_message(message: str) -> SafetyResult:

    if not isinstance(message, str) or not message.strip():

        raise ValueError("Message cannot be empty.")

    if detect_prompt_injection(message):

        return SafetyResult(
            allowed=False,
            category=SafetyCategory.PROMPT_INJECTION,
            response=PROMPT_INJECTION_RESPONSE,
        )

    if detect_unsafe_request(message):

        return SafetyResult(
            allowed=False,
            category=SafetyCategory.UNSAFE_REQUEST,
            response=UNSAFE_REQUEST_RESPONSE,
        )

    if detect_out_of_scope_request(message):

        return SafetyResult(
            allowed=False,
            category=SafetyCategory.OUT_OF_SCOPE,
            response=OUT_OF_SCOPE_RESPONSE,
        )

    return SafetyResult(
        allowed=True,
        category=SafetyCategory.SAFE,
    )


# ---------------------------------------------------------
# OUTPUT PRIVACY CHECKS
# ---------------------------------------------------------

SENSITIVE_OUTPUT_PATTERNS = [

    # Google API keys.
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),

    # Private key blocks.
    re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        re.IGNORECASE,
    ),

    # Explicit API key assignments.
    re.compile(
        r"(?:GEMINI_API_KEY|OPENAI_API_KEY|API_KEY)"
        r"\s*=\s*\S+",
        re.IGNORECASE,
    ),

    # Bearer authentication tokens.
    re.compile(
        r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}",
        re.IGNORECASE,
    ),

]


def contains_sensitive_information(answer: str) -> bool:

    return any(
        pattern.search(answer)
        for pattern in SENSITIVE_OUTPUT_PATTERNS
    )


def validate_output(answer: str) -> SafetyResult:

    if not isinstance(answer, str) or not answer.strip():

        raise ValueError("Generated response cannot be empty.")

    if contains_sensitive_information(answer):

        return SafetyResult(
            allowed=False,
            category=SafetyCategory.SENSITIVE_OUTPUT,
            response=OUTPUT_SECURITY_RESPONSE,
        )

    return SafetyResult(
        allowed=True,
        category=SafetyCategory.SAFE,
    )