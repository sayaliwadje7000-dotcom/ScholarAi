import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database.session import SessionLocal
from app.models.study_resource import StudyResource


@pytest.fixture
def db_session():
    session = SessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_study_resource_database_persistence(db_session):
    resource = StudyResource(
        title="Introduction to Python",
        description="Python programming fundamentals.",
        resource_type="tutorial",
        url="https://example.com/python",
        provider="Example Academy",
        subject="Computer Science",
        language="English",
        difficulty_level="beginner",
        estimated_duration_minutes=45,
        quality_score=4.75,
        resource_metadata={
            "topics": ["variables", "loops", "functions"],
            "verified": True,
        },
    )

    db_session.add(resource)
    db_session.commit()

    resource_id = resource.id

    retrieved = db_session.execute(
        select(StudyResource).where(
            StudyResource.id == resource_id
        )
    ).scalar_one()

    assert retrieved.title == "Introduction to Python"
    assert retrieved.resource_type == "tutorial"
    assert retrieved.subject == "Computer Science"
    assert retrieved.quality_score == 4.75
    assert retrieved.resource_metadata["verified"] is True

    retrieved.resource_metadata["difficulty_note"] = "Easy"

    db_session.commit()
    db_session.refresh(retrieved)

    assert retrieved.resource_metadata["difficulty_note"] == "Easy"

    db_session.delete(retrieved)
    db_session.commit()

    assert db_session.get(StudyResource, resource_id) is None


@pytest.mark.parametrize(
    "resource_type",
    ["invalid", "random", ""],
)
def test_invalid_resource_type_rejected(db_session, resource_type):
    resource = StudyResource(
        title="Invalid Resource",
        resource_type=resource_type,
        url="https://example.com",
    )

    db_session.add(resource)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_empty_title_rejected(db_session):
    resource = StudyResource(
        title="   ",
        resource_type="video",
        url="https://example.com",
    )

    db_session.add(resource)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_empty_url_rejected(db_session):
    resource = StudyResource(
        title="Valid title",
        resource_type="video",
        url="   ",
    )

    db_session.add(resource)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


@pytest.mark.parametrize(
    "difficulty",
    ["easy", "expert", "invalid"],
)
def test_invalid_difficulty_rejected(db_session, difficulty):
    resource = StudyResource(
        title="Test Resource",
        resource_type="video",
        url="https://example.com",
        difficulty_level=difficulty,
    )

    db_session.add(resource)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_negative_duration_rejected(db_session):
    resource = StudyResource(
        title="Test Resource",
        resource_type="video",
        url="https://example.com",
        estimated_duration_minutes=-10,
    )

    db_session.add(resource)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


@pytest.mark.parametrize(
    "score",
    [-1, 5.01, 10],
)
def test_invalid_quality_score_rejected(db_session, score):
    resource = StudyResource(
        title="Test Resource",
        resource_type="video",
        url="https://example.com",
        quality_score=score,
    )

    db_session.add(resource)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_metadata_must_be_object():
    with pytest.raises(ValueError):
        StudyResource(
            title="Test Resource",
            resource_type="video",
            url="https://example.com",
            resource_metadata=["invalid", "metadata"],
        )


def test_inactive_resource_can_be_stored(db_session):
    resource = StudyResource(
        title="Archived Resource",
        resource_type="article",
        url="https://example.com/article",
        is_active=False,
    )

    db_session.add(resource)
    db_session.commit()

    assert resource.is_active is False