"""
ScholarAI authentication schemas.

Defines request and response contracts for registration
and login operations.
"""

from uuid import UUID
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    field_validator,
)

from app.security.password_policy import (
    validate_password,
)


class UserRegistrationRequest(BaseModel):
    """
    Incoming user registration payload.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    full_name: str = Field(
        min_length=2,
        max_length=150,
    )

    email: EmailStr

    password: SecretStr

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:

        value = value.strip()

        if not value:
            raise ValueError(
                "Full name cannot be empty."
            )

        if not any(
            character.isalpha()
            for character in value
        ):
            raise ValueError(
                "Full name must contain alphabetic characters."
            )

        return value

    @field_validator("email")
    @classmethod
    def normalize_registration_email(
        cls,
        value: EmailStr,
    ) -> str:

        return str(value).strip().casefold()

    @field_validator("password")
    @classmethod
    def validate_registration_password(
        cls,
        value: SecretStr,
    ) -> SecretStr:

        validate_password(
            value.get_secret_value()
        )

        return value


class UserLoginRequest(BaseModel):
    """
    Incoming login credentials.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    email: EmailStr

    password: SecretStr

    @field_validator("email")
    @classmethod
    def normalize_login_email(
        cls,
        value: EmailStr,
    ) -> str:

        return str(value).strip().casefold()


class UserRegistrationResponse(BaseModel):
    """
    Public user information returned after registration.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID

    full_name: str

    email: EmailStr

    is_active: bool

    created_at: datetime


class UserLoginResponse(BaseModel):
    """
    Response after successful authentication and JWT issuance.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    authenticated: bool

    message: str

    user: UserRegistrationResponse

    access_token: str

    token_type: str = "bearer"

    expires_in: int