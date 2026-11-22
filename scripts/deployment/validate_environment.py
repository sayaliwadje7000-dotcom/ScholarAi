"""
ScholarAI Production Environment Validator.

Validates production configuration without exposing secrets.

Usage:
    python scripts/deployment/validate_environment.py
"""

import os

from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ============================================================
# LOAD PROJECT ENVIRONMENT
# ============================================================

def load_project_environment() -> None:

    environment_file = PROJECT_ROOT / ".env"

    if environment_file.exists():

        load_dotenv(
            environment_file,
            override=False,
        )


# ============================================================
# VALIDATE ENVIRONMENT
# ============================================================

def validate_environment(
    environment: Mapping[str, str] | None = None,
) -> list[str]:

    env = (
        environment
        if environment is not None
        else os.environ
    )

    errors: list[str] = []

    current_environment = env.get(
        "SCHOLARAI_ENVIRONMENT",
        "development",
    ).strip().lower()

    allowed_environments = {
        "development",
        "testing",
        "production",
    }

    if current_environment not in allowed_environments:

        errors.append(
            "SCHOLARAI_ENVIRONMENT must be development, "
            "testing, or production."
        )

        return errors

    # Production-only validation.

    if current_environment != "production":

        return errors

    # --------------------------------------------------------
    # REQUIRED VARIABLES
    # --------------------------------------------------------

    required_variables = [
        "DATABASE_URL",
        "SCHOLARAI_JWT_SECRET_KEY",
        "SCHOLARAI_FRONTEND_ORIGIN",
        "POSTGRES_PASSWORD",
        "GEMINI_API_KEY",
    ]

    for variable in required_variables:

        if not env.get(variable, "").strip():

            errors.append(
                f"Missing required production variable: {variable}"
            )

    # --------------------------------------------------------
    # DEBUG VALIDATION
    # --------------------------------------------------------

    debug_value = env.get(
        "SCHOLARAI_DEBUG",
        "false",
    ).strip().lower()

    if debug_value not in {
        "false",
        "0",
        "no",
        "off",
    }:

        errors.append(
            "SCHOLARAI_DEBUG must be false in production."
        )

    # --------------------------------------------------------
    # JWT VALIDATION
    # --------------------------------------------------------

    jwt_secret = env.get(
        "SCHOLARAI_JWT_SECRET_KEY",
        "",
    )

    if jwt_secret and len(jwt_secret.encode("utf-8")) < 32:

        errors.append(
            "SCHOLARAI_JWT_SECRET_KEY must contain "
            "at least 32 bytes."
        )

    if jwt_secret and (
        "REPLACE_WITH" in jwt_secret
        or "CHANGE_ME" in jwt_secret
    ):

        errors.append(
            "SCHOLARAI_JWT_SECRET_KEY contains a placeholder."
        )

    # --------------------------------------------------------
    # FRONTEND ORIGIN VALIDATION
    # --------------------------------------------------------

    frontend_origin = env.get(
        "SCHOLARAI_FRONTEND_ORIGIN",
        "",
    ).strip()

    if frontend_origin:

        try:

            parsed_frontend = urlsplit(
                frontend_origin
            )

            valid_frontend = (
                parsed_frontend.scheme == "https"
                and bool(parsed_frontend.hostname)
                and parsed_frontend.username is None
                and parsed_frontend.password is None
                and parsed_frontend.path in {"", "/"}
                and not parsed_frontend.query
                and not parsed_frontend.fragment
            )

            if not valid_frontend:

                errors.append(
                    "SCHOLARAI_FRONTEND_ORIGIN must be a valid "
                    "HTTPS origin without credentials, path, "
                    "query, or fragment."
                )

            elif parsed_frontend.port is not None and not (
                1 <= parsed_frontend.port <= 65535
            ):

                errors.append(
                    "SCHOLARAI_FRONTEND_ORIGIN has an invalid port."
                )

        except ValueError:

            errors.append(
                "SCHOLARAI_FRONTEND_ORIGIN is malformed."
            )

    # --------------------------------------------------------
    # DATABASE URL VALIDATION
    # --------------------------------------------------------

    database_url = env.get(
        "DATABASE_URL",
        "",
    ).strip()

    if database_url:

        try:

            parsed_database = urlsplit(
                database_url
            )

            if parsed_database.scheme not in {
                "postgresql",
                "postgresql+psycopg",
            }:

                errors.append(
                    "DATABASE_URL must use PostgreSQL "
                    "or postgresql+psycopg."
                )

            if not parsed_database.hostname:

                errors.append(
                    "DATABASE_URL must contain a hostname."
                )

            if parsed_database.port is not None and not (
                1 <= parsed_database.port <= 65535
            ):

                errors.append(
                    "DATABASE_URL contains an invalid port."
                )

            if not parsed_database.path or parsed_database.path == "/":

                errors.append(
                    "DATABASE_URL must specify a database name."
                )

        except ValueError:

            errors.append(
                "DATABASE_URL is malformed."
            )

    # --------------------------------------------------------
    # DATABASE PASSWORD VALIDATION
    # --------------------------------------------------------

    postgres_password = env.get(
        "POSTGRES_PASSWORD",
        "",
    )

    if postgres_password in {
        "CHANGE_ME",
        "password",
        "postgres",
    }:

        errors.append(
            "POSTGRES_PASSWORD must be replaced "
            "with a strong unique password."
        )

    # --------------------------------------------------------
    # GEMINI PLACEHOLDER VALIDATION
    # --------------------------------------------------------

    gemini_key = env.get(
        "GEMINI_API_KEY",
        "",
    ).strip()

    if gemini_key and (
        "CHANGE_ME" in gemini_key
        or "REPLACE_WITH" in gemini_key
    ):

        errors.append(
            "GEMINI_API_KEY contains a placeholder."
        )

    return errors


# ============================================================
# COMMAND LINE ENTRY POINT
# ============================================================

def main() -> int:

    load_project_environment()

    errors = validate_environment()

    if errors:

        print(
            "SCHOLARAI ENVIRONMENT VALIDATION FAILED"
        )

        for index, error in enumerate(
            errors,
            start=1,
        ):

            print(f"{index}. {error}")

        return 1

    print(
        "SCHOLARAI ENVIRONMENT VALIDATION PASSED"
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(main())
