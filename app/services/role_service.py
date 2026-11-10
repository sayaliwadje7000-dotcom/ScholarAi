"""
ScholarAI Role Management Service.
"""

import uuid

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_role import UserRole

from app.security.roles import normalize_role

from app.security.authorization_exceptions import (
    RoleNotFoundError,
    RoleAlreadyAssignedError,
    LastAdministratorError,
)


class RoleService:

    def get_user_roles(
        self,
        db: Session,
        user_id: uuid.UUID,
    ) -> set[str]:

        roles = db.scalars(
            select(UserRole.role).where(
                UserRole.user_id == user_id
            )
        ).all()

        return set(roles)

    def assign_role(
        self,
        db: Session,
        user_id: uuid.UUID,
        role: str,
    ) -> UserRole:

        normalized_role = normalize_role(role)

        user = db.scalar(
            select(User).where(User.id == user_id)
        )

        if user is None:
            raise RoleNotFoundError(
                "User not found."
            )

        existing = db.scalar(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role == normalized_role,
            )
        )

        if existing is not None:
            raise RoleAlreadyAssignedError(
                "Role is already assigned."
            )

        assignment = UserRole(
            user_id=user_id,
            role=normalized_role,
        )

        try:
            db.add(assignment)
            db.commit()
            db.refresh(assignment)

            return assignment

        except Exception:
            db.rollback()
            raise

    def revoke_role(
        self,
        db: Session,
        user_id: uuid.UUID,
        role: str,
    ) -> bool:

        normalized_role = normalize_role(role)

        assignment = db.scalar(
            select(UserRole)
            .where(
                UserRole.user_id == user_id,
                UserRole.role == normalized_role,
            )
            .with_for_update()
        )

        if assignment is None:
            return False

        if normalized_role == "admin":

            admin_count = db.scalar(
                select(func.count())
                .select_from(UserRole)
                .where(UserRole.role == "admin")
            )

            if admin_count <= 1:
                raise LastAdministratorError(
                    "Cannot revoke the last administrator."
                )

        try:

            db.delete(assignment)
            db.commit()

            return True

        except Exception:
            db.rollback()
            raise

    def list_user_roles(
        self,
        db: Session,
        user_id: uuid.UUID,
    ) -> list[str]:

        return sorted(
            self.get_user_roles(db, user_id)
        )


role_service = RoleService()
