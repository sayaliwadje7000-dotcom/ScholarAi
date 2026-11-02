import uuid

import pytest

from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from app.database.session import SessionLocal

from app.models.user import User
from app.models.learning_activity import LearningActivity


def test_learning_activity_database_persistence():

    email = f"phase68_{uuid.uuid4().hex}@example.com"

    db = SessionLocal()

    user_id = None
    activity_id = None

    try:

        # Create user.

        user = User(
            full_name="Learning Activity Test User",
            email=email,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        user_id = user.id

        # Create learning activity.

        activity = LearningActivity(
            user_id=user_id,
            activity_type="document_upload",
            entity_type="document",
            entity_id=uuid.uuid4(),
            duration_seconds=15,
            activity_metadata={
                "filename": "data_structures.pdf",
                "pages": 25,
                "subject": "Data Structures",
            },
        )

        db.add(activity)
        db.commit()
        db.refresh(activity)

        activity_id = activity.id

        # Verify generated values.

        assert isinstance(activity.id, uuid.UUID)

        assert activity.user_id == user_id

        assert activity.activity_type == "document_upload"

        assert activity.entity_type == "document"

        assert isinstance(activity.entity_id, uuid.UUID)

        assert activity.duration_seconds == 15

        assert activity.activity_metadata["filename"] == (
            "data_structures.pdf"
        )

        assert activity.occurred_at is not None

        # Retrieve activity.

        retrieved = db.get(
            LearningActivity,
            activity_id,
        )

        assert retrieved is not None

        assert retrieved.user.id == user_id

        # Verify reverse relationship.

        db.refresh(user)

        assert any(
            item.id == activity_id
            for item in user.learning_activities
        )

        # Verify JSONB update.

        retrieved.activity_metadata["pages"] = 30

        db.commit()
        db.refresh(retrieved)

        assert retrieved.activity_metadata["pages"] == 30

        # Verify duration update.

        retrieved.duration_seconds = 120

        db.commit()
        db.refresh(retrieved)

        assert retrieved.duration_seconds == 120

        # Verify negative duration rejection.

        invalid_duration = LearningActivity(
            user_id=user_id,
            activity_type="study_session",
            duration_seconds=-10,
        )

        db.add(invalid_duration)

        with pytest.raises(IntegrityError):
            db.commit()

        db.rollback()

        # Verify empty activity type rejection.

        invalid_type = LearningActivity(
            user_id=user_id,
            activity_type="   ",
        )

        db.add(invalid_type)

        with pytest.raises(IntegrityError):
            db.commit()

        db.rollback()

        # Verify incomplete entity reference rejection.

        invalid_entity = LearningActivity(
            user_id=user_id,
            activity_type="document_upload",
            entity_type="document",
            entity_id=None,
        )

        db.add(invalid_entity)

        with pytest.raises(IntegrityError):
            db.commit()

        db.rollback()

        # Verify invalid entity type rejection.

        invalid_entity_type = LearningActivity(
            user_id=user_id,
            activity_type="document_upload",
            entity_type="   ",
            entity_id=uuid.uuid4(),
        )

        db.add(invalid_entity_type)

        with pytest.raises(IntegrityError):
            db.commit()

        db.rollback()

        # Verify invalid user foreign key.

        invalid_user_activity = LearningActivity(
            user_id=uuid.uuid4(),
            activity_type="study_session",
        )

        db.add(invalid_user_activity)

        with pytest.raises(IntegrityError):
            db.commit()

        db.rollback()

        # Verify activity without entity reference.

        standalone_activity = LearningActivity(
            user_id=user_id,
            activity_type="study_session",
            activity_metadata={
                "subject": "Mathematics",
            },
        )

        db.add(standalone_activity)
        db.commit()
        db.refresh(standalone_activity)

        assert standalone_activity.entity_type is None
        assert standalone_activity.entity_id is None

        # Verify cascade deletion.

        db.execute(
            delete(User)
            .where(User.id == user_id)
            .execution_options(synchronize_session=False)
        )

        db.commit()

        assert db.get(User, user_id) is None

        assert db.get(
            LearningActivity,
            activity_id,
        ) is None

    finally:

        db.rollback()

        if user_id is not None:

            remaining_user = db.get(User, user_id)

            if remaining_user is not None:
                db.delete(remaining_user)
                db.commit()

        db.close()