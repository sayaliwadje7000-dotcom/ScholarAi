import os


class Settings:
    """Central configuration for the ScholarAI backend."""

    APP_NAME: str = "ScholarAI"
    APP_VERSION: str = "0.1.0"

    # Frontend development server.
    FRONTEND_ORIGIN: str = os.getenv(
        "SCHOLARAI_FRONTEND_ORIGIN",
        "http://127.0.0.1:5500",
    )

    # Backend development server.
    BACKEND_HOST: str = os.getenv(
        "SCHOLARAI_BACKEND_HOST",
        "127.0.0.1",
    )

    BACKEND_PORT: int = int(
        os.getenv("SCHOLARAI_BACKEND_PORT", "8000")
    )


settings = Settings()