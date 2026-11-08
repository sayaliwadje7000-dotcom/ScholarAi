from uuid import uuid4

from app.services.recommendations.ml.privacy.privacy_audit import (
    RecommendationPrivacyAuditor,
)


def test_complete_privacy_audit_passes():
    auditor = RecommendationPrivacyAuditor()

    # 8 training samples
    training_users = [uuid4() for _ in range(8)]
    training_resources = [uuid4() for _ in range(8)]

    # 2 validation samples
    # Separate users prevent user leakage.
    validation_users = [uuid4(), uuid4()]
    validation_resources = [uuid4(), uuid4()]

    result = auditor.audit(
        training_user_ids=training_users,
        training_resource_ids=training_resources,
        validation_user_ids=validation_users,
        validation_resource_ids=validation_resources,
        feature_names=[
            "resource_quality",
            "historical_click_count",
        ],
        metadata={
            "stage": "baseline",
            "email": "student@example.com",
        },
    )

    assert result.passed is True

    assert (
        result.sanitized_metadata["email"]
        == "[REDACTED]"
    )

    assert result.dataset_report.shared_users == 0


def test_audit_report_serialization():
    auditor = RecommendationPrivacyAuditor()

    # 9 training samples
    training_users = [uuid4() for _ in range(9)]
    training_resources = [uuid4() for _ in range(9)]

    # 1 validation sample
    validation_users = [uuid4()]
    validation_resources = [uuid4()]

    result = auditor.audit(
        training_user_ids=training_users,
        training_resource_ids=training_resources,
        validation_user_ids=validation_users,
        validation_resource_ids=validation_resources,
        feature_names=[
            "resource_quality",
        ],
        metadata={
            "phase": "14.8",
        },
    )

    serialized = result.to_dict()

    assert serialized["passed"] is True

    assert serialized["dataset_report"]["shared_users"] == 0

    assert serialized["feature_report"]["is_safe"] is True

    assert serialized["sanitized_metadata"]["phase"] == "14.8"