import os

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OCRSettings:
    tesseract_cmd: str
    language: str
    dpi: int
    timeout_seconds: int
    minimum_confidence: float
    force_ocr: bool


def load_ocr_settings() -> OCRSettings:

    tesseract_cmd = os.getenv(
        "TESSERACT_CMD",
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    )

    language = os.getenv(
        "OCR_LANGUAGE",
        "eng",
    )

    dpi = int(
        os.getenv("OCR_DPI", "300")
    )

    timeout_seconds = int(
        os.getenv("OCR_TIMEOUT_SECONDS", "60")
    )

    minimum_confidence = float(
        os.getenv("OCR_MINIMUM_CONFIDENCE", "40")
    )

    force_ocr = os.getenv(
        "OCR_FORCE",
        "false",
    ).strip().lower() in {
        "true",
        "1",
        "yes",
    }

    if dpi < 72 or dpi > 600:
        raise ValueError(
            "OCR_DPI must be between 72 and 600."
        )

    if timeout_seconds <= 0:
        raise ValueError(
            "OCR_TIMEOUT_SECONDS must be positive."
        )

    if not 0 <= minimum_confidence <= 100:
        raise ValueError(
            "OCR_MINIMUM_CONFIDENCE must be between 0 and 100."
        )

    if not language.strip():
        raise ValueError(
            "OCR_LANGUAGE cannot be empty."
        )

    if not tesseract_cmd.strip():
        raise ValueError(
            "TESSERACT_CMD cannot be empty."
        )

    return OCRSettings(
        tesseract_cmd=tesseract_cmd,
        language=language,
        dpi=dpi,
        timeout_seconds=timeout_seconds,
        minimum_confidence=minimum_confidence,
        force_ocr=force_ocr,
    )


ocr_settings = load_ocr_settings()