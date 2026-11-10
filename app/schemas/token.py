"""
JWT token response schemas.
"""

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class AccessTokenResponse(BaseModel):

    model_config = ConfigDict(
        extra="forbid",
    )

    access_token: str = Field(
        min_length=1,
    )

    token_type: str = Field(
        default="bearer",
    )

    expires_in: int = Field(
        gt=0,
        description="Token lifetime in seconds.",
    )