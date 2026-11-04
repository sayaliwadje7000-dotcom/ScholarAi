from typing import NoReturn

from fastapi import HTTPException, status


def get_current_user() -> NoReturn:
    """
    Authentication placeholder.

    JWT authentication will be implemented after Phase 7.

    Document API endpoints depend on this function, so they
    cannot accidentally become publicly accessible before
    genuine authentication is implemented.
    """

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Authentication is not implemented yet. "
            "Document endpoints will be available after "
            "the authentication phase."
        ),
    )