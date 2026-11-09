import pytest

from pydantic import ValidationError

from app.schemas.personalization_controls import (
    PersonalizationControlsUpdate,
)


def test_valid_controls_update():

    request = PersonalizationControlsUpdate(
        preferred_language="English",
        education_level="Undergraduate",
        preferred_subjects=[
            "Data Structures",
            "Artificial Intelligence",
        ],
        notification_enabled=True,
    )

    assert request.preferred_language == "English"
    assert request.education_level == "Undergraduate"
    assert len(request.preferred_subjects) == 2
    assert request.notification_enabled is True


def test_subjects_are_normalized():

    request = PersonalizationControlsUpdate(
        preferred_subjects=[
            " Data Structures ",
            "Artificial Intelligence",
            "data structures",
        ]
    )

    assert request.preferred_subjects == [
        "Data Structures",
        "Artificial Intelligence",
    ]


def test_empty_subject_is_rejected():

    with pytest.raises(ValidationError):

        PersonalizationControlsUpdate(
            preferred_subjects=[
                "Data Structures",
                " ",
            ]
        )


def test_non_string_subject_is_rejected():

    with pytest.raises(ValidationError):

        PersonalizationControlsUpdate(
            preferred_subjects=[
                "Data Structures",
                123,
            ]
        )


def test_language_is_normalized():

    request = PersonalizationControlsUpdate(
        preferred_language=" English "
    )

    assert request.preferred_language == "English"


def test_empty_language_becomes_none():

    request = PersonalizationControlsUpdate(
        preferred_language=" "
    )

    assert request.preferred_language is None


def test_notification_can_be_disabled():

    request = PersonalizationControlsUpdate(
        notification_enabled=False
    )

    assert request.notification_enabled is False


def test_partial_update_is_supported():

    request = PersonalizationControlsUpdate(
        preferred_language="Marathi"
    )

    updates = request.model_dump(
        exclude_unset=True
    )

    assert updates == {
        "preferred_language": "Marathi"
    }


def test_null_subject_list_is_allowed():

    request = PersonalizationControlsUpdate(
        preferred_subjects=None
    )

    assert request.preferred_subjects is None