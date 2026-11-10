from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.services.behavioral_signal_service import (
    BehavioralSignalService,
    LearningActivityEntityNotFoundError,
)


@pytest.mark.parametrize(
    "entity_type",
    ["document", "recommendation"],
)
def test_learning_activity_rejects_private_entity_not_owned_by_user(
    entity_type,
):
    db = Mock()
    db.scalar.return_value = None
    user_id = uuid4()
    entity_id = uuid4()
    request = SimpleNamespace(
        entity_type=entity_type,
        entity_id=entity_id,
        activity_type=SimpleNamespace(value="study_session_started"),
        duration_seconds=None,
        activity_metadata={},
    )

    with pytest.raises(LearningActivityEntityNotFoundError):
        BehavioralSignalService().record_activity(
            db=db,
            user_id=user_id,
            request=request,
        )

    db.add.assert_not_called()
    db.flush.assert_not_called()
    db.scalar.assert_called_once()


@pytest.mark.parametrize(
    "entity_type",
    ["document", "recommendation"],
)
def test_learning_activity_accepts_private_entity_owned_by_user(
    entity_type,
):
    db = Mock()
    db.scalar.return_value = uuid4()
    request = SimpleNamespace(
        entity_type=entity_type,
        entity_id=uuid4(),
        activity_type=SimpleNamespace(value="study_session_started"),
        duration_seconds=30,
        activity_metadata={},
    )

    activity = BehavioralSignalService().record_activity(
        db=db,
        user_id=uuid4(),
        request=request,
    )

    assert activity.user_id is not None
    assert activity.entity_type == entity_type
    db.add.assert_called_once_with(activity)
    db.flush.assert_called_once()
