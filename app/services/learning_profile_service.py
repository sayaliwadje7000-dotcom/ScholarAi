from datetime import datetime, timezone
from uuid import UUID, uuid5, NAMESPACE_URL

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_preferences import UserPreferences

from app.schemas.learning_profile import (
    LearningGoalCreate,
    LearningGoalResponse,
    LearningGoalUpdate,
    LearningProfileUpdate,
    LearningProfileResponse,
)


class LearningProfileService:
    """
    Application service responsible for managing:

    - Student learning profiles
    - Learning preferences
    - Structured learning goals

    Existing UserPreferences storage is reused.
    """

    # ========================================================
    # PREFERENCES
    # ========================================================

    @staticmethod
    def _get_or_create_preferences(
        db: Session,
        user: User,
    ) -> UserPreferences:

        preferences = db.scalar(
            select(UserPreferences).where(
                UserPreferences.user_id == user.id
            )
        )

        if preferences is not None:
            return preferences

        preferences = UserPreferences(
            user_id=user.id,
            preferred_subjects=[],
            learning_goals=[],
            notification_enabled=True,
        )

        db.add(preferences)

        db.flush()

        return preferences

    # ========================================================
    # LEGACY GOAL CONVERSION
    # ========================================================

    @staticmethod
    def _convert_legacy_goal(
        user_id: UUID,
        value,
    ) -> dict | None:

        if isinstance(value, str):

            title = value.strip()

            if not title:
                return None

            # Deterministic ID prevents legacy goals
            # receiving a different ID on every read.

            goal_id = uuid5(
                NAMESPACE_URL,
                f"scholarai:{user_id}:legacy-goal:{title.casefold()}",
            )

            now = datetime.now(timezone.utc)

            return {
                "id": str(goal_id),
                "title": title,
                "description": None,
                "subject": None,
                "priority": "medium",
                "status": "active",
                "target_date": None,
                "progress_percent": 0,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }

        if isinstance(value, dict):
            return value

        return None

    @classmethod
    def _normalize_goals(
        cls,
        user_id: UUID,
        stored_goals,
    ) -> list[LearningGoalResponse]:

        if not isinstance(stored_goals, list):
            return []

        normalized = []

        for value in stored_goals:

            goal = cls._convert_legacy_goal(
                user_id,
                value,
            )

            if goal is None:
                continue

            try:

                normalized_goal = (
                    LearningGoalResponse.model_validate(goal)
                )

                normalized.append(normalized_goal)

            except (ValueError, TypeError):
                # Invalid legacy entries are not exposed.
                continue

        return normalized

    # ========================================================
    # SERIALIZATION
    # ========================================================

    @staticmethod
    def _serialize_goals(goals):

        return [
            goal.model_dump(mode="json")
            for goal in goals
        ]

    # ========================================================
    # GET PROFILE
    # ========================================================

    def get_profile(
        self,
        db: Session,
        user: User,
    ) -> LearningProfileResponse:

        preferences = self._get_or_create_preferences(
            db,
            user,
        )

        goals = self._normalize_goals(
            user.id,
            preferences.learning_goals,
        )

        return LearningProfileResponse(
            user_id=user.id,
            preferred_language=(
                preferences.preferred_language
            ),
            education_level=(
                preferences.education_level
            ),
            preferred_subjects=(
                preferences.preferred_subjects or []
            ),
            notification_enabled=(
                preferences.notification_enabled
            ),
            learning_goals=goals,
            created_at=preferences.created_at,
            updated_at=preferences.updated_at,
        )

    # ========================================================
    # UPDATE PROFILE
    # ========================================================

    def update_profile(
        self,
        db: Session,
        user: User,
        request: LearningProfileUpdate,
    ) -> LearningProfileResponse:

        preferences = self._get_or_create_preferences(
            db,
            user,
        )

        updates = request.model_dump(
            exclude_unset=True,
        )

        for field, value in updates.items():

            setattr(
                preferences,
                field,
                value,
            )

        preferences.updated_at = datetime.now(
            timezone.utc
        )

        db.flush()

        return self.get_profile(
            db,
            user,
        )

    # ========================================================
    # LIST GOALS
    # ========================================================

    def list_goals(
        self,
        db: Session,
        user: User,
    ) -> list[LearningGoalResponse]:

        preferences = self._get_or_create_preferences(
            db,
            user,
        )

        return self._normalize_goals(
            user.id,
            preferences.learning_goals,
        )

    # ========================================================
    # CREATE GOAL
    # ========================================================

    def create_goal(
        self,
        db: Session,
        user: User,
        request: LearningGoalCreate,
    ) -> LearningGoalResponse:

        preferences = self._get_or_create_preferences(
            db,
            user,
        )

        existing_goals = self._normalize_goals(
            user.id,
            preferences.learning_goals,
        )

        now = datetime.now(timezone.utc)

        goal_data = request.model_dump(
            mode="json",
        )

        goal_data.update(
            {
                "id": str(UUID(bytes=__import__("os").urandom(16), version=4)),
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
        )

        new_goal = LearningGoalResponse.model_validate(
            goal_data
        )

        existing_goals.append(new_goal)

        preferences.learning_goals = (
            self._serialize_goals(existing_goals)
        )

        preferences.updated_at = now

        db.flush()

        return new_goal

    # ========================================================
    # UPDATE GOAL
    # ========================================================

    def update_goal(
        self,
        db: Session,
        user: User,
        goal_id: UUID,
        request: LearningGoalUpdate,
    ) -> LearningGoalResponse | None:

        preferences = self._get_or_create_preferences(
            db,
            user,
        )

        goals = self._normalize_goals(
            user.id,
            preferences.learning_goals,
        )

        target = None

        updates = request.model_dump(
            exclude_unset=True,
            mode="json",
        )

        if not updates:
            return next(
                (
                    goal
                    for goal in goals
                    if goal.id == goal_id
                ),
                None,
            )

        for index, goal in enumerate(goals):

            if goal.id != goal_id:
                continue

            goal_data = goal.model_dump(
                mode="json",
            )

            goal_data.update(updates)

            goal_data["updated_at"] = datetime.now(
                timezone.utc
            ).isoformat()

            # Revalidate status/progress consistency.
            target = LearningGoalResponse.model_validate(
                goal_data
            )

            goals[index] = target

            break

        if target is None:
            return None

        preferences.learning_goals = (
            self._serialize_goals(goals)
        )

        preferences.updated_at = datetime.now(
            timezone.utc
        )

        db.flush()

        return target

    # ========================================================
    # DELETE GOAL
    # ========================================================

    def delete_goal(
        self,
        db: Session,
        user: User,
        goal_id: UUID,
    ) -> bool:

        preferences = self._get_or_create_preferences(
            db,
            user,
        )

        goals = self._normalize_goals(
            user.id,
            preferences.learning_goals,
        )

        updated_goals = [
            goal
            for goal in goals
            if goal.id != goal_id
        ]

        if len(updated_goals) == len(goals):
            return False

        preferences.learning_goals = (
            self._serialize_goals(updated_goals)
        )

        preferences.updated_at = datetime.now(
            timezone.utc
        )

        db.flush()

        return True