import uuid

import pytest

from app.models.user_preferences import UserPreferences

from app.schemas.personalization_controls import (
    PersonalizationControlsUpdate,
)

from app.services.personalization_controls_service import (
    PersonalizationControlsService,
)


class FakeSession:
    """Lightweight in-memory session for service unit tests."""

    def __init__(self):
        self.preferences = {}
        self.added = []
        self.committed = False
        self.rolled_back = False

    def scalar(self, statement):
        """
        Resolve the user ID from the SQLAlchemy query
        and return that user's preferences.
        """

        where_clause = statement.whereclause

        user_id = where_clause.right.value

        return self.preferences.get(user_id)

    def add(self, instance):
        self.added.append(instance)

        if isinstance(instance, UserPreferences):
            self.preferences[instance.user_id] = instance

    def flush(self):
        pass

    def commit(self):
        self.committed = True

    def refresh(self, instance):
        pass

    def rollback(self):
        self.rolled_back = True


@pytest.fixture
def db_session():

    db = FakeSession()
    user_id = uuid.uuid4()

    yield db, user_id


def test_get_controls_creates_default_preferences(db_session):

    db, user_id = db_session

    preferences = (
        PersonalizationControlsService.get_controls(
            db=db,
            user_id=user_id,
        )
    )

    assert preferences.user_id == user_id
    assert preferences.preferred_subjects == []
    assert preferences.learning_goals == []
    assert preferences.notification_enabled is True

    assert db.committed is True


def test_update_controls(db_session):

    db, user_id = db_session

    request = PersonalizationControlsUpdate(
        preferred_language="English",
        education_level="Undergraduate",
        preferred_subjects=[
            "Data Structures",
        ],
        notification_enabled=False,
    )

    preferences = (
        PersonalizationControlsService.update_controls(
            db=db,
            user_id=user_id,
            request=request,
        )
    )

    assert preferences.preferred_language == "English"
    assert preferences.education_level == "Undergraduate"

    assert preferences.preferred_subjects == [
        "Data Structures",
    ]

    assert preferences.notification_enabled is False
    assert db.committed is True


def test_partial_update_preserves_other_preferences(db_session):

    db, user_id = db_session

    PersonalizationControlsService.update_controls(
        db=db,
        user_id=user_id,
        request=PersonalizationControlsUpdate(
            preferred_language="English",
            preferred_subjects=["Mathematics"],
            notification_enabled=True,
        ),
    )

    preferences = (
        PersonalizationControlsService.update_controls(
            db=db,
            user_id=user_id,
            request=PersonalizationControlsUpdate(
                preferred_language="Marathi",
            ),
        )
    )

    assert preferences.preferred_language == "Marathi"

    assert preferences.preferred_subjects == [
        "Mathematics",
    ]

    assert preferences.notification_enabled is True


def test_reset_controls_preserves_learning_goals(db_session):

    db, user_id = db_session

    preferences = UserPreferences(
        user_id=user_id,
        preferred_language="English",
        education_level="Undergraduate",
        preferred_subjects=["Mathematics"],
        learning_goals=[
            {
                "id": str(uuid.uuid4()),
                "title": "Improve programming",
                "priority": "high",
                "status": "active",
                "progress_percentage": 20,
            }
        ],
        notification_enabled=False,
    )

    db.add(preferences)

    reset_preferences = (
        PersonalizationControlsService.reset_controls(
            db=db,
            user_id=user_id,
        )
    )

    assert reset_preferences.preferred_language is None
    assert reset_preferences.education_level is None
    assert reset_preferences.preferred_subjects == []
    assert reset_preferences.notification_enabled is True

    assert len(reset_preferences.learning_goals) == 1

    assert (
        reset_preferences.learning_goals[0]["title"]
        == "Improve programming"
    )


def test_user_preferences_are_isolated(db_session):

    db, first_user_id = db_session

    second_user_id = uuid.uuid4()

    PersonalizationControlsService.update_controls(
        db=db,
        user_id=first_user_id,
        request=PersonalizationControlsUpdate(
            preferred_language="English",
        ),
    )

    second_preferences = (
        PersonalizationControlsService.get_controls(
            db=db,
            user_id=second_user_id,
        )
    )

    assert second_preferences.preferred_language is None

    first_preferences = db.preferences[first_user_id]

    assert first_preferences.preferred_language == "English"