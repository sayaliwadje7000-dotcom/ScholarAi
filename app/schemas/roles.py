"""
ScholarAI RBAC API schemas.
"""

import uuid

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.security.roles import normalize_role


class RoleAssignmentRequest(BaseModel):

    role: str = Field(
        min_length=1,
        max_length=30,
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, value):

        return normalize_role(value)


class RoleAssignmentResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    role: str
    created_at: datetime


class UserRolesResponse(BaseModel):

    user_id: uuid.UUID
    roles: list[str]


class RoleOperationResponse(BaseModel):

    message: str
    user_id: uuid.UUID
    role: str
