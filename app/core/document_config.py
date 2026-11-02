import os

from dataclasses import dataclass
from pathlib import Path


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ============================================================
# CONFIGURATION VALIDATION
# ============================================================

def get_positive_integer(
    name: str,
    default: int,
) -> int:
    """
    Read a positive integer from an environment variable.

    Raises ValueError for invalid or non-positive values.
    """

    raw_value = os.getenv(
        name,
        str(default),
    ).strip()

    try:
        value = int(raw_value)

    except ValueError as exc:
        raise ValueError(
            f"{name} must be a valid integer."
        ) from exc

    if value <= 0:
        raise ValueError(
            f"{name} must be greater than zero."
        )

    return value


def get_boolean(
    name: str,
    default: bool,
) -> bool:
    """
    Read a boolean environment variable.
    """

    raw_value = os.getenv(
        name,
        str(default),
    ).strip().lower()

    if raw_value in {"true", "1", "yes", "on"}:
        return True

    if raw_value in {"false", "0", "no", "off"}:
        return False

    raise ValueError(
        f"{name} must be a valid boolean."
    )


# ============================================================
# DOCUMENT CONFIGURATION
# ============================================================

@dataclass(frozen=True)
class DocumentSettings:
    """
    Central configuration for ScholarAI document processing.
    """

    storage_root: Path

    max_file_size_bytes: int

    max_pages: int

    allowed_extensions: tuple[str, ...]

    allowed_mime_types: tuple[str, ...]

    create_storage_directories: bool


def load_document_settings() -> DocumentSettings:
    """
    Load document settings from environment variables.

    Relative storage paths are resolved against PROJECT_ROOT.
    """

    configured_root = os.getenv(
        "DOCUMENT_STORAGE_ROOT",
        "storage",
    ).strip()

    if not configured_root:
        raise ValueError(
            "DOCUMENT_STORAGE_ROOT cannot be empty."
        )

    storage_root = Path(
        configured_root
    ).expanduser()

    if not storage_root.is_absolute():
        storage_root = (
            PROJECT_ROOT / storage_root
        )

    storage_root = storage_root.resolve()

    return DocumentSettings(
        storage_root=storage_root,

        max_file_size_bytes=get_positive_integer(
            "MAX_DOCUMENT_SIZE_BYTES",
            20 * 1024 * 1024,
        ),

        max_pages=get_positive_integer(
            "MAX_DOCUMENT_PAGES",
            100,
        ),

        allowed_extensions=(".pdf",),

        allowed_mime_types=(
            "application/pdf",
        ),

        create_storage_directories=get_boolean(
            "CREATE_DOCUMENT_STORAGE",
            True,
        ),
    )


# ============================================================
# STORAGE DIRECTORIES
# ============================================================

def get_storage_directories(
    settings: DocumentSettings,
) -> dict[str, Path]:
    """
    Return the paths for all document storage categories.
    """

    root = settings.storage_root

    return {
        "root": root,

        "documents": root / "documents",

        "processed": root / "processed",

        "temporary": root / "temporary",
    }


def initialize_document_storage(
    settings: DocumentSettings | None = None,
) -> dict[str, Path]:
    """
    Initialize document storage directories.

    This function does not overwrite existing files.
    """

    if settings is None:
        settings = load_document_settings()

    directories = get_storage_directories(
        settings
    )

    if not settings.create_storage_directories:
        return directories

    try:
        for directory in directories.values():

            directory.mkdir(
                parents=True,
                exist_ok=True,
            )

            if not directory.is_dir():
                raise RuntimeError(
                    f"Storage path is not a directory: {directory}"
                )

    except OSError as exc:
        raise RuntimeError(
            "Unable to initialize document storage."
        ) from exc

    return directories


# ============================================================
# APPLICATION DOCUMENT SETTINGS
# ============================================================

document_settings = load_document_settings()