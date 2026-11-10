"""
Phase 18.6 session API schemas.
"""

import uuid

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RefreshTokenRequest(BaseModel):

    refresh_token: str = Field(
        min_length=20,
        max_length=8192,
    )


class SessionResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime
    revoked_at: datetime | None
    revoke_reason: str | None


class SessionListResponse(BaseModel):

    sessions: list[SessionResponse]


class SessionRevocationResponse(BaseModel):

    message: str
    session_id: uuid.UUID | None = None


class TokenPairResponse(BaseModel):

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_at: datetime
