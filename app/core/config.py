"""
ScholarAI Central Configuration Module.

Responsibilities:
- Load environment variables.
- Parse environment configuration.
- Validate application settings.
- Provide immutable application settings.
- Preserve compatibility with existing imports.
"""

import os

from dataclasses import dataclass
from dotenv import load_dotenv


# ============================================================
# ENVIRONMENT LOADING
# ============================================================

load_dotenv()


# ============================================================
# BOOLEAN PARSER
# ============================================================

def get_boolean(name: str, default: bool = False) -> bool:

    raw_value = os.getenv(
        name,
        str(default),
    ).strip().lower()

    true_values = {"true", "1", "yes", "on"}
    false_values = {"false", "0", "no", "off"}

    if raw_value in true_values:
        return True

    if raw_value in false_values:
        return False

    raise ValueError(
        f"{name} must contain a valid boolean value."
    )


# ============================================================
# INTEGER PARSER
# ============================================================

def get_integer(
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:

    raw_value = os.getenv(
        name,
        str(default),
    ).strip()

    try:
        value = int(raw_value)

    except ValueError as exc:

        raise ValueError(
            f"{name} must be an integer."
        ) from exc

    if not minimum <= value <= maximum:

        raise ValueError(
            f"{name} must be between "
            f"{minimum} and {maximum}."
        )

    return value


# ============================================================
# SETTINGS MODEL
# ============================================================

@dataclass(frozen=True)
class Settings:
    """
    Immutable application-level configuration.
    """

    APP_NAME: str = "ScholarAI"

    APP_VERSION: str = "0.1.0"

    ENVIRONMENT: str = "development"

    DEBUG: bool = False

    FRONTEND_ORIGIN: str = "http://127.0.0.1:5500"

    BACKEND_HOST: str = "127.0.0.1"

    BACKEND_PORT: int = 8000

    DATABASE_URL: str = ""

    LOG_LEVEL: str = "INFO"


# ============================================================
# SETTINGS LOADER
# ============================================================

def load_settings() -> Settings:

    environment = os.getenv(
        "SCHOLARAI_ENVIRONMENT",
        "development",
    ).strip().lower()

    allowed_environments = {
        "development",
        "testing",
        "production",
    }

    if environment not in allowed_environments:

        raise ValueError(
            "SCHOLARAI_ENVIRONMENT must be "
            "development, testing, or production."
        )

    debug = get_boolean(
        "SCHOLARAI_DEBUG",
        False,
    )

    frontend_origin = os.getenv(
        "SCHOLARAI_FRONTEND_ORIGIN",
        "http://127.0.0.1:5500",
    ).strip()

    backend_host = os.getenv(
        "SCHOLARAI_BACKEND_HOST",
        "127.0.0.1",
    ).strip()

    backend_port = get_integer(
        "SCHOLARAI_BACKEND_PORT",
        8000,
        1,
        65535,
    )

    database_url = os.getenv(
        "DATABASE_URL",
        "",
    ).strip()

    log_level = os.getenv(
        "LOG_LEVEL",
        "INFO",
    ).strip().upper()

    if not frontend_origin:

        raise ValueError(
            "SCHOLARAI_FRONTEND_ORIGIN cannot be empty."
        )

    if not backend_host:

        raise ValueError(
            "SCHOLARAI_BACKEND_HOST cannot be empty."
        )

    allowed_log_levels = {
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    }

    if log_level not in allowed_log_levels:

        raise ValueError(
            "LOG_LEVEL must be DEBUG, INFO, WARNING, "
            "ERROR, or CRITICAL."
        )

    if environment == "production":

        if debug:

            raise ValueError(
                "Debug mode cannot be enabled in production."
            )

        if not frontend_origin.startswith("https://"):

            raise ValueError(
                "Production frontend origin must use HTTPS."
            )

    return Settings(
        ENVIRONMENT=environment,
        DEBUG=debug,
        FRONTEND_ORIGIN=frontend_origin,
        BACKEND_HOST=backend_host,
        BACKEND_PORT=backend_port,
        DATABASE_URL=database_url,
        LOG_LEVEL=log_level,
    )


# ============================================================
# APPLICATION SETTINGS INSTANCE
# ============================================================

settings = load_settings()
