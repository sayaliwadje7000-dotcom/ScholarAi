"""
ScholarAI Administrative Role Management API.

All endpoints require an existing administrator role.
"""

import logging
import uuid

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from sqlalchemy.orm import Session

from app.database.session import get_db

from app.models.user import User

from app.schemas.roles import (
    RoleAssignmentRequest,
    RoleAssignmentResponse,
    UserRolesResponse,
    RoleOperationResponse,
)

from app.security.permissions import require_admin

from app.security.authorization_exceptions import (
    RoleNotFoundError,
    RoleAlreadyAssignedError,
    LastAdministratorError,
)

from app.services.role_service import role_service


logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/users/{user_id}/roles",
    response_model=UserRolesResponse,
)
def get_user_roles(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):

    roles = role_service.list_user_roles(
        db=db,
        user_id=user_id,
    )

    return UserRolesResponse(
        user_id=user_id,
        roles=roles,
    )


@router.post(
    "/users/{user_id}/roles",
    response_model=RoleAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def assign_user_role(
    user_id: uuid.UUID,
    request: RoleAssignmentRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):

    try:

        assignment = role_service.assign_role(
            db=db,
            user_id=user_id,
            role=request.role,
        )

        return RoleAssignmentResponse.model_validate(
            assignment
        )

    except RoleNotFoundError as exc:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except RoleAlreadyAssignedError as exc:

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        logger.exception("Role assignment failed.")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to assign role.",
        ) from exc


@router.delete(
    "/users/{user_id}/roles/{role}",
    response_model=RoleOperationResponse,
)
def revoke_user_role(
    user_id: uuid.UUID,
    role: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):

    try:

        revoked = role_service.revoke_role(
            db=db,
            user_id=user_id,
            role=role,
        )

        if not revoked:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role assignment not found.",
            )

        return RoleOperationResponse(
            message="Role revoked successfully.",
            user_id=user_id,
            role=role,
        )

    except LastAdministratorError as exc:

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except HTTPException:
        raise

    except Exception as exc:

        logger.exception("Role revocation failed.")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to revoke role.",
        ) from exc
