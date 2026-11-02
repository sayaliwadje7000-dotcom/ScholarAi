from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


if not settings.DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is missing. Check your .env configuration."
    )


engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
)


SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """
    Provides a database session to API endpoints.

    Automatically closes the session after use.
    """

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()