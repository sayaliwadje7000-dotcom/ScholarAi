import uuid

import pytest

from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from app.database.session import SessionLocal

from app.models.user import User
from app.models.user_preferences import UserPreferences


def test_user_preferences_database_persistence():

    email = f"phase66_{uuid.uuid4().hex}@example.com"

    db = SessionLocal()

    user_id = None
    preferences_id = None

    try:

        # Create user

        user = User(
            full_name="Preferences Test User",
            email=email,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        user_id = user.id

        # Create preferences

        preferences = UserPreferences(
            user_id=user_id,
            preferred_language="English",
            education_level="Undergraduate",
            preferred_subjects=[
                "Data Structures",
                "Artificial Intelligence",
            ],
            learning_goals=[
                "Prepare for examinations",
                "Improve programming skills",
            ],
            notification_enabled=True,
        )

        db.add(preferences)
        db.commit()
        db.refresh(preferences)

        preferences_id = preferences.id

        # Verify generated values

        assert isinstance(preferences.id, uuid.UUID)

        assert preferences.user_id == user_id

        assert preferences.preferred_language == "English"

        assert preferences.education_level == "Undergraduate"

        assert "Data Structures" in preferences.preferred_subjects

        assert "Prepare for examinations" in preferences.learning_goals

        assert preferences.notification_enabled is True

        assert preferences.created_at is not None

        assert preferences.updated_at is not None

        # Retrieve preferences

        retrieved = db.get(
            UserPreferences,
            preferences_id,
        )

        assert retrieved is not None

        assert retrieved.user.id == user_id

        # Verify reverse relationship

        db.refresh(user)

        assert user.preferences.id == preferences_id

        # Verify JSONB in-place modification

        retrieved.preferred_subjects.append("Database Management")

        db.commit()
        db.refresh(retrieved)

        assert "Database Management" in retrieved.preferred_subjects

        # Verify update

        retrieved.preferred_language = "Marathi"

        retrieved.notification_enabled = False

        db.commit()
        db.refresh(retrieved)

        assert retrieved.preferred_language == "Marathi"

        assert retrieved.notification_enabled is False

        # Verify one-to-one uniqueness constraint

        duplicate_preferences = UserPreferences(
            user_id=user_id,
            preferred_language="Hindi",
        )

        db.add(duplicate_preferences)

        with pytest.raises(IntegrityError):
            db.commit()

        db.rollback()

        # Verify invalid user foreign key

        invalid_preferences = UserPreferences(
            user_id=uuid.uuid4(),
            preferred_language="English",
        )

        db.add(invalid_preferences)

        with pytest.raises(IntegrityError):
            db.commit()

        db.rollback()

        # Verify database cascade deletion

        db.execute(
            delete(User)
            .where(User.id == user_id)
            .execution_options(synchronize_session=False)
        )

        db.commit()

        assert db.get(User, user_id) is None

        assert db.get(UserPreferences, preferences_id) is None

    finally:

        db.rollback()

        if user_id is not None:

            remaining_user = db.get(User, user_id)

            if remaining_user is not None:
                db.delete(remaining_user)
                db.commit()

        db.close()