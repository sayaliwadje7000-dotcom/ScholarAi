import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.database.session import SessionLocal
from app.models.user import User


def test_user_database_persistence():
    test_email = f"phase63_{uuid.uuid4().hex}@example.com"

    db = SessionLocal()
    user_id = None

    try:
        # 1. Create a user.
        user = User(
            full_name="ScholarAI Test User",
            email=test_email,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        user_id = user.id

        assert isinstance(user.id, uuid.UUID)
        assert user.full_name == "ScholarAI Test User"
        assert user.email == test_email
        assert user.is_active is True
        assert user.created_at is not None
        assert user.updated_at is not None

        # 2. Retrieve the user from PostgreSQL.
        retrieved_user = db.get(User, user_id)

        assert retrieved_user is not None
        assert retrieved_user.email == test_email

        # 3. Update the user.
        retrieved_user.full_name = "Updated ScholarAI User"

        db.commit()
        db.refresh(retrieved_user)

        assert retrieved_user.full_name == "Updated ScholarAI User"

        # 4. Verify duplicate email rejection.
        duplicate_user = User(
            full_name="Duplicate User",
            email=test_email,
        )

        db.add(duplicate_user)

        with pytest.raises(IntegrityError):
            db.commit()

        db.rollback()

        # 5. Delete the original user.
        original_user = db.get(User, user_id)

        assert original_user is not None

        db.delete(original_user)
        db.commit()

        # 6. Verify deletion.
        assert db.get(User, user_id) is None

    finally:
        db.rollback()

        if user_id is not None:
            remaining_user = db.get(User, user_id)

            if remaining_user is not None:
                db.delete(remaining_user)
                db.commit()

        db.close()