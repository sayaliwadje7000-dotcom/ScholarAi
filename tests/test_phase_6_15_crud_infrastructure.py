from sqlalchemy import text

from app.database.session import SessionLocal


def test_database_session_can_execute_queries():

    db = SessionLocal()

    try:
        result = db.execute(
            text("SELECT 1")
        ).scalar()

        assert result == 1

    finally:
        db.close()


def test_database_session_transaction():

    db = SessionLocal()

    try:
        with db.begin():
            result = db.execute(
                text("SELECT 100")
            ).scalar()

            assert result == 100

    finally:
        db.close()


def test_database_session_rollback():

    db = SessionLocal()

    try:
        db.execute(
            text("SELECT 1")
        )

        db.rollback()

        assert db.is_active

    finally:
        db.close()