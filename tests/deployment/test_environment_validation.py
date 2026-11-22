import runpy

from pathlib import Path

import pytest


# ============================================================
# VALIDATOR IMPORT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

VALIDATOR_PATH = (
    PROJECT_ROOT
    / "scripts"
    / "deployment"
    / "validate_environment.py"
)

VALIDATOR_NAMESPACE = runpy.run_path(
    str(VALIDATOR_PATH)
)

validate_environment = VALIDATOR_NAMESPACE[
    "validate_environment"
]


# ============================================================
# VALID PRODUCTION ENVIRONMENT
# ============================================================

@pytest.fixture
def valid_production_environment():

    return {
        "SCHOLARAI_ENVIRONMENT": "production",

        "SCHOLARAI_DEBUG": "false",

        "SCHOLARAI_FRONTEND_ORIGIN": (
            "https://scholarai.example.com"
        ),

        "DATABASE_URL": (
            "postgresql+psycopg://"
            "scholarai:StrongPassword123"
            "@database.example.com:5432/scholarai"
        ),

        "SCHOLARAI_JWT_SECRET_KEY": (
            "a-secure-random-secret-with-more-than-32-bytes"
        ),

        "POSTGRES_PASSWORD": (
            "AnotherStrongPassword123"
        ),

        "GEMINI_API_KEY": (
            "valid-example-api-key"
        ),
    }


# ============================================================
# DEVELOPMENT ENVIRONMENT
# ============================================================

def test_development_environment_does_not_require_production_secrets():

    environment = {
        "SCHOLARAI_ENVIRONMENT": "development",
    }

    assert validate_environment(environment) == []


# ============================================================
# TESTING ENVIRONMENT
# ============================================================

def test_testing_environment_does_not_require_production_secrets():

    environment = {
        "SCHOLARAI_ENVIRONMENT": "testing",
    }

    assert validate_environment(environment) == []


# ============================================================
# VALID PRODUCTION CONFIGURATION
# ============================================================

def test_valid_production_configuration(
    valid_production_environment,
):

    errors = validate_environment(
        valid_production_environment
    )

    assert errors == []


# ============================================================
# REQUIRED VARIABLES
# ============================================================

def test_missing_required_variables_are_reported():

    environment = {
        "SCHOLARAI_ENVIRONMENT": "production",
        "SCHOLARAI_DEBUG": "false",
    }

    errors = validate_environment(
        environment
    )

    assert any(
        "DATABASE_URL" in error
        for error in errors
    )

    assert any(
        "SCHOLARAI_JWT_SECRET_KEY" in error
        for error in errors
    )

    assert any(
        "GEMINI_API_KEY" in error
        for error in errors
    )


# ============================================================
# JWT VALIDATION
# ============================================================

def test_short_jwt_secret_is_rejected(
    valid_production_environment,
):

    valid_production_environment[
        "SCHOLARAI_JWT_SECRET_KEY"
    ] = "short"

    errors = validate_environment(
        valid_production_environment
    )

    assert any(
        "32 bytes" in error
        for error in errors
    )


def test_jwt_placeholder_is_rejected(
    valid_production_environment,
):

    valid_production_environment[
        "SCHOLARAI_JWT_SECRET_KEY"
    ] = "REPLACE_WITH_A_RANDOM_SECRET_AT_LEAST_32_BYTES"

    errors = validate_environment(
        valid_production_environment
    )

    assert any(
        "placeholder" in error.lower()
        for error in errors
    )


# ============================================================
# DEBUG VALIDATION
# ============================================================

def test_production_debug_mode_is_rejected(
    valid_production_environment,
):

    valid_production_environment[
        "SCHOLARAI_DEBUG"
    ] = "true"

    errors = validate_environment(
        valid_production_environment
    )

    assert any(
        "DEBUG" in error
        for error in errors
    )


# ============================================================
# HTTPS VALIDATION
# ============================================================

def test_http_frontend_origin_is_rejected(
    valid_production_environment,
):

    valid_production_environment[
        "SCHOLARAI_FRONTEND_ORIGIN"
    ] = "http://scholarai.example.com"

    errors = validate_environment(
        valid_production_environment
    )

    assert any(
        "HTTPS" in error
        for error in errors
    )


def test_frontend_origin_with_path_is_rejected(
    valid_production_environment,
):

    valid_production_environment[
        "SCHOLARAI_FRONTEND_ORIGIN"
    ] = "https://scholarai.example.com/app"

    errors = validate_environment(
        valid_production_environment
    )

    assert any(
        "HTTPS origin" in error
        for error in errors
    )


# ============================================================
# DATABASE VALIDATION
# ============================================================

def test_non_postgresql_database_is_rejected(
    valid_production_environment,
):

    valid_production_environment[
        "DATABASE_URL"
    ] = "mysql://user:password@localhost/database"

    errors = validate_environment(
        valid_production_environment
    )

    assert any(
        "PostgreSQL" in error
        for error in errors
    )


def test_database_without_hostname_is_rejected(
    valid_production_environment,
):

    valid_production_environment[
        "DATABASE_URL"
    ] = "postgresql+psycopg:///scholarai"

    errors = validate_environment(
        valid_production_environment
    )

    assert any(
        "hostname" in error
        for error in errors
    )


def test_database_without_name_is_rejected(
    valid_production_environment,
):

    valid_production_environment[
        "DATABASE_URL"
    ] = "postgresql+psycopg://user:password@localhost"

    errors = validate_environment(
        valid_production_environment
    )

    assert any(
        "database name" in error
        for error in errors
    )


# ============================================================
# DATABASE PASSWORD VALIDATION
# ============================================================

def test_default_database_password_is_rejected(
    valid_production_environment,
):

    valid_production_environment[
        "POSTGRES_PASSWORD"
    ] = "CHANGE_ME"

    errors = validate_environment(
        valid_production_environment
    )

    assert any(
        "POSTGRES_PASSWORD" in error
        for error in errors
    )


# ============================================================
# GEMINI VALIDATION
# ============================================================

def test_missing_gemini_api_key_is_rejected(
    valid_production_environment,
):

    valid_production_environment[
        "GEMINI_API_KEY"
    ] = ""

    errors = validate_environment(
        valid_production_environment
    )

    assert any(
        "GEMINI_API_KEY" in error
        for error in errors
    )


# ============================================================
# ENVIRONMENT NAME VALIDATION
# ============================================================

def test_invalid_environment_name_is_rejected():

    environment = {
        "SCHOLARAI_ENVIRONMENT": "staging",
    }

    errors = validate_environment(
        environment
    )

    assert any(
        "SCHOLARAI_ENVIRONMENT" in error
        for error in errors
    )
