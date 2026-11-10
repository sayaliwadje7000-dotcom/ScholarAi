"""
JWT token exceptions.
"""


class TokenError(Exception):
    """Base exception for token-related failures."""


class TokenCreationError(TokenError):
    """Raised when an access token cannot be created."""


class TokenValidationError(TokenError):
    """Raised when an access token is invalid."""