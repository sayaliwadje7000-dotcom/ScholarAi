
from uuid import uuid4

import pytest

from app.services.recommendations.ml.privacy.dataset_privacy import (
    DatasetPrivacyValidator,
)

from app.services.recommendations.ml.privacy.privacy_exceptions import (
    DatasetPrivacyError,
    IdentifierLeakageError,
)


def make_dataset():
    """
    Create a valid dataset satisfying the default privacy configuration.

    Training:
        8 samples
        8 distinct users

    Validation:
        2 samples
        2 distinct users

    Total:
        10 samples
        No user overlap between training and validation.
    """

    training_users = [
        uuid4()
        for _ in range(8)
    ]

    training_resources = [
        uuid4()
        for _ in range(8)
    ]

    validation_users = [
        uuid4(),
        uuid4(),
    ]

    validation_resources = [
        uuid4(),
        uuid4(),
    ]

    return (
        training_users,
        training_resources,
        validation_users,
        validation_resources,
    )


def test_valid_dataset_passes():
    validator = DatasetPrivacyValidator()

    (
        training_users,
        training_resources,
        validation_users,
        validation_resources,
    ) = make_dataset()

    report = validator.validate(
        training_user_ids=training_users,
        training_resource_ids=training_resources,
        validation_user_ids=validation_users,
        validation_resource_ids=validation_resources,
        feature_names=[
            "resource_quality",
            "historical_click_count",
        ],
    )

    assert report.is_safe is True
    assert report.shared_users == 0
    assert report.duplicate_training_pairs == 0
    assert report.duplicate_validation_pairs == 0


def test_shared_users_are_rejected():
    validator = DatasetPrivacyValidator()

    (
        training_users,
        training_resources,
        validation_users,
        validation_resources,
    ) = make_dataset()

    validation_users[0] = training_users[0]

    with pytest.raises(DatasetPrivacyError):
        validator.validate(
            training_user_ids=training_users,
            training_resource_ids=training_resources,
            validation_user_ids=validation_users,
            validation_resource_ids=validation_resources,
            feature_names=[
                "resource_quality",
            ],
        )


def test_duplicate_training_pairs_are_rejected():
    validator = DatasetPrivacyValidator()

    (
        training_users,
        training_resources,
        validation_users,
        validation_resources,
    ) = make_dataset()

    training_users[1] = training_users[0]
    training_resources[1] = training_resources[0]

    with pytest.raises(DatasetPrivacyError):
        validator.validate(
            training_user_ids=training_users,
            training_resource_ids=training_resources,
            validation_user_ids=validation_users,
            validation_resource_ids=validation_resources,
            feature_names=[
                "resource_quality",
            ],
        )


def test_duplicate_validation_pairs_are_rejected():
    validator = DatasetPrivacyValidator()

    (
        training_users,
        training_resources,
        validation_users,
        validation_resources,
    ) = make_dataset()

    validation_users[1] = validation_users[0]
    validation_resources[1] = validation_resources[0]

    with pytest.raises(DatasetPrivacyError):
        validator.validate(
            training_user_ids=training_users,
            training_resource_ids=training_resources,
            validation_user_ids=validation_users,
            validation_resource_ids=validation_resources,
            feature_names=[
                "resource_quality",
            ],
        )


def test_identifier_features_are_rejected():
    validator = DatasetPrivacyValidator()

    (
        training_users,
        training_resources,
        validation_users,
        validation_resources,
    ) = make_dataset()

    with pytest.raises(IdentifierLeakageError):
        validator.validate(
            training_user_ids=training_users,
            training_resource_ids=training_resources,
            validation_user_ids=validation_users,
            validation_resource_ids=validation_resources,
            feature_names=[
                "user_id",
                "resource_quality",
            ],
        )


def test_insufficient_training_users_are_rejected():
    validator = DatasetPrivacyValidator()

    # Four training samples are sufficient to test the
    # minimum-distinct-user rule without triggering the
    # combined minimum-sample rule first.
    training_users = [
        uuid4(),
        uuid4(),
        uuid4(),
    ]

    training_resources = [
        uuid4(),
        uuid4(),
        uuid4(),
    ]

    validation_users = [
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
    ]

    validation_resources = [
        uuid4()
        for _ in range(7)
    ]

    with pytest.raises(DatasetPrivacyError):
        validator.validate(
            training_user_ids=training_users,
            training_resource_ids=training_resources,
            validation_user_ids=validation_users,
            validation_resource_ids=validation_resources,
            feature_names=[
                "resource_quality",
            ],
        )


def test_identifier_arrays_must_align():
    validator = DatasetPrivacyValidator()

    (
        training_users,
        training_resources,
        validation_users,
        validation_resources,
    ) = make_dataset()

    training_resources.pop()

    with pytest.raises(DatasetPrivacyError):
        validator.validate(
            training_user_ids=training_users,
            training_resource_ids=training_resources,
            validation_user_ids=validation_users,
            validation_resource_ids=validation_resources,
            feature_names=[
                "resource_quality",
            ],
        )


def test_non_uuid_identifiers_are_rejected():
    validator = DatasetPrivacyValidator()

    with pytest.raises(DatasetPrivacyError):
        validator.validate(
            training_user_ids=[
                "user-1"
                for _ in range(8)
            ],
            training_resource_ids=[
                uuid4()
                for _ in range(8)
            ],
            validation_user_ids=[
                uuid4(),
                uuid4(),
            ],
            validation_resource_ids=[
                uuid4(),
                uuid4(),
            ],
            feature_names=[
                "resource_quality",
            ],
        )
