from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user_preferences import UserPreferences

from app.schemas.personalization_controls import (
    PersonalizationControlsUpdate,
)


class PersonalizationControlsError(Exception):
    """Base exception for personalization controls."""


class PersonalizationPreferencesNotFoundError(
    PersonalizationControlsError
):
    """Raised when a preference record cannot be found."""


class PersonalizationControlsService:
    """
    Manages student-controlled personalization preferences.

    All operations are scoped to the authenticated user's ID.
    """

    @staticmethod
    def get_or_create_preferences(
        db: Session,
        user_id,
    ) -> UserPreferences:

        preferences = db.scalar(
            select(UserPreferences).where(
                UserPreferences.user_id == user_id
            )
        )

        if preferences is None:
            preferences = UserPreferences(
                user_id=user_id,
                preferred_language=None,
                education_level=None,
                preferred_subjects=[],
                learning_goals=[],
                notification_enabled=True,
            )

            db.add(preferences)
            db.flush()

        return preferences

    @classmethod
    def get_controls(
        cls,
        db: Session,
        user_id,
    ) -> UserPreferences:

        try:
            preferences = cls.get_or_create_preferences(
                db=db,
                user_id=user_id,
            )

            db.commit()
            db.refresh(preferences)

            return preferences

        except Exception:
            db.rollback()
            raise

    @classmethod
    def update_controls(
        cls,
        db: Session,
        user_id,
        request: PersonalizationControlsUpdate,
    ) -> UserPreferences:

        try:
            preferences = cls.get_or_create_preferences(
                db=db,
                user_id=user_id,
            )

            updates = request.model_dump(
                exclude_unset=True
            )

            for field, value in updates.items():

                if field == "preferred_subjects":
                    if value is not None:
                        preferences.preferred_subjects = value

                elif field == "preferred_language":
                    preferences.preferred_language = value

                elif field == "education_level":
                    preferences.education_level = value

                elif field == "notification_enabled":
                    if value is not None:
                        preferences.notification_enabled = value

            db.add(preferences)
            db.commit()
            db.refresh(preferences)

            return preferences

        except Exception:
            db.rollback()
            raise

    @classmethod
    def reset_controls(
        cls,
        db: Session,
        user_id,
    ) -> UserPreferences:

        try:
            preferences = cls.get_or_create_preferences(
                db=db,
                user_id=user_id,
            )

            preferences.preferred_language = None
            preferences.education_level = None
            preferences.preferred_subjects = []
            preferences.notification_enabled = True

            # Learning goals are intentionally preserved.
            # They are managed separately through Phase 16.2.

            db.add(preferences)
            db.commit()
            db.refresh(preferences)

            return preferences

        except Exception:
            db.rollback()
            raise