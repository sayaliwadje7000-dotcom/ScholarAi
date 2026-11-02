from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session, configure_mappers

from app.main import app as fastapi_app
from app.database.base import Base
from app.database.session import engine, SessionLocal, get_db
import app.models


# --------------------------------------------------
# 1. DATABASE CONNECTION TESTS
# --------------------------------------------------

def test_database_connection():
    """Verify that PostgreSQL is reachable."""

    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT 1")
        ).scalar()

    assert result == 1


def test_database_engine_initialized():
    """Verify SQLAlchemy engine initialization."""

    assert engine is not None
    assert engine.dialect.name == "postgresql"


# --------------------------------------------------
# 2. SESSION MANAGEMENT TESTS
# --------------------------------------------------

def test_session_factory_creates_session():
    """Verify that SessionLocal creates a valid session."""

    db = SessionLocal()

    try:
        assert isinstance(db, Session)

        result = db.execute(
            text("SELECT 1")
        ).scalar()

        assert result == 1

    finally:
        db.close()


def test_get_db_yields_session():
    """Verify that the database dependency yields a session."""

    generator = get_db()

    db = next(generator)

    try:
        assert isinstance(db, Session)

        result = db.execute(
            text("SELECT 1")
        ).scalar()

        assert result == 1

    finally:
        generator.close()

    assert db.is_active is False or not db.in_transaction()


# --------------------------------------------------
# 3. TRANSACTION ROLLBACK TEST
# --------------------------------------------------

def test_database_transaction_rollback():
    """
    Verify PostgreSQL transaction rollback using
    a temporary table.

    No permanent application table is modified.
    """

    with engine.connect() as connection:

        connection.execute(
            text("""
                CREATE TEMPORARY TABLE
                scholarai_phase615_transaction_test (
                    id INTEGER PRIMARY KEY
                )
            """)
        )

        connection.commit()

        try:
            with connection.begin():

                connection.execute(
                    text("""
                        INSERT INTO scholarai_phase615_transaction_test
                        (id)
                        VALUES (1)
                    """)
                )

                count = connection.execute(
                    text("""
                        SELECT COUNT(*)
                        FROM scholarai_phase615_transaction_test
                    """)
                ).scalar()

                assert count == 1

                raise RuntimeError(
                    "Simulated transaction failure"
                )

        except RuntimeError:
            pass

        remaining = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM scholarai_phase615_transaction_test
            """)
        ).scalar()

        assert remaining == 0

        connection.execute(
            text("""
                DROP TABLE scholarai_phase615_transaction_test
            """)
        )

        connection.commit()


# --------------------------------------------------
# 4. MODEL REGISTRATION TESTS
# --------------------------------------------------

def test_all_models_are_registered():
    """Verify that all expected application models are registered."""

    expected_tables = {
        "users",
        "user_preferences",
        "conversations",
        "messages",
        "documents",
        "learning_activities",
        "study_resources",
        "resource_categories",
        "study_resource_categories",
        "user_resource_interactions",
        "recommendations",
        "recommendation_feedback",
    }

    actual_tables = set(Base.metadata.tables.keys())

    assert expected_tables.issubset(actual_tables)


def test_all_relationships_configure():
    """Verify SQLAlchemy relationships."""

    configure_mappers()


# --------------------------------------------------
# 5. FASTAPI DATABASE HEALTH TESTS
# --------------------------------------------------

def test_database_health_endpoint():
    """Verify the PostgreSQL health endpoint."""

    client = TestClient(fastapi_app)

    response = client.get("/health/database")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_general_health_endpoint():
    """Verify the general health endpoint."""

    client = TestClient(fastapi_app)

    response = client.get("/health")

    assert response.status_code == 200

    assert response.json()["status"] == "healthy"


def test_home_endpoint():
    """Verify the ScholarAI home endpoint."""

    client = TestClient(fastapi_app)

    response = client.get("/")

    assert response.status_code == 200

    assert response.json()["application"] == "ScholarAI"