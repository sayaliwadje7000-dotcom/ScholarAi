"""
Provision the first ScholarAI administrator.

Usage:
python -m scripts.provision_admin student@example.com
"""

import sys

from sqlalchemy import select

from app.database.session import SessionLocal

from app.models.user import User
from app.models.user_role import UserRole


def main():

    if len(sys.argv) != 2:
        print(
            "Usage: python -m scripts.provision_admin <email>"
        )
        raise SystemExit(1)

    email = sys.argv[1].strip().lower()

    db = SessionLocal()

    try:

        user = db.scalar(
            select(User).where(User.email == email)
        )

        if user is None:
            print("User not found.")
            raise SystemExit(1)

        existing = db.scalar(
            select(UserRole).where(
                UserRole.user_id == user.id,
                UserRole.role == "admin",
            )
        )

        if existing is not None:
            print("User is already an administrator.")
            return

        db.add(
            UserRole(
                user_id=user.id,
                role="admin",
            )
        )

        db.commit()

        print(
            f"Administrator role assigned to {email}."
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
