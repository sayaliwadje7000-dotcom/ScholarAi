import uuid

from sqlalchemy import select

from app.database.session import SessionLocal
from app.models import User


def verify_user_persistence():

    session = SessionLocal()

    try:
        unique_email = (
            f"phase63-{uuid.uuid4().hex}@example.test"
        )

        # 1. Insert user.
        user = User(
            full_name="ScholarAI Test User",
            email=unique_email,
        )

        session.add(user)
        session.commit()
        session.refresh(user)

        user_id = user.id

        assert isinstance(user_id, uuid.UUID)

        print("USER INSERTION: PASSED")

        # 2. Retrieve user.
        retrieved_user = session.execute(
            select(User).where(User.id == user_id)
        ).scalar_one()

        assert retrieved_user.email == unique_email

        print("USER RETRIEVAL: PASSED")

        # 3. Verify default account status.
        assert retrieved_user.is_active is True

        print("DEFAULT ACCOUNT STATUS: PASSED")

        # 4. Verify timestamps.
        assert retrieved_user.created_at is not None
        assert retrieved_user.updated_at is not None

        print("TIMESTAMP GENERATION: PASSED")

        # 5. Update user.
        retrieved_user.full_name = "Updated ScholarAI User"

        session.commit()
        session.refresh(retrieved_user)

        assert retrieved_user.full_name == "Updated ScholarAI User"

        print("USER UPDATE: PASSED")

        # 6. Verify duplicate email rejection.
        duplicate_user = User(
            full_name="Duplicate User",
            email=unique_email,
        )

        session.add(duplicate_user)

        try:
            session.commit()
            raise AssertionError("Duplicate email was accepted")

        except Exception:
            session.rollback()

        print("EMAIL UNIQUENESS: PASSED")

        # 7. Delete test user.
        user_to_delete = session.get(User, user_id)

        if user_to_delete is not None:
            session.delete(user_to_delete)
            session.commit()

        assert session.get(User, user_id) is None

        print("USER DELETION: PASSED")

        print("--------------------------------")
        print("ALL USER PERSISTENCE TESTS PASSED")

    finally:
        session.close()


if __name__ == "__main__":
    verify_user_persistence()