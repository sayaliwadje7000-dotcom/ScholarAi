from datetime import datetime, timedelta, timezone

import pytest

from app.services.recommendations.ml.privacy.feature_leakage import (
    FeatureLeakageDetector,
)

from app.services.recommendations.ml.privacy.privacy_exceptions import (
    IdentifierLeakageError,
    TargetLeakageError,
    TemporalLeakageError,
)


def test_safe_features_pass():

    detector = FeatureLeakageDetector()

    report = detector.validate(
        [
            "resource_quality",
            "historical_click_count",
            "subject_similarity",
            "estimated_duration",
        ]
    )

    assert report.is_safe is True


def test_user_id_is_rejected():

    detector = FeatureLeakageDetector()

    with pytest.raises(IdentifierLeakageError):

        detector.validate(
            [
                "user_id",
                "resource_quality",
            ]
        )


def test_resource_id_is_rejected():

    detector = FeatureLeakageDetector()

    with pytest.raises(IdentifierLeakageError):

        detector.validate(
            [
                "resource_id",
                "resource_quality",
            ]
        )


def test_email_is_rejected():

    detector = FeatureLeakageDetector()

    with pytest.raises(IdentifierLeakageError):

        detector.validate(
            [
                "email",
                "resource_quality",
            ]
        )


def test_target_label_is_rejected():

    detector = FeatureLeakageDetector()

    with pytest.raises(TargetLeakageError):

        detector.validate(
            [
                "resource_quality",
                "relevance_label",
            ]
        )


def test_future_feature_is_rejected():

    detector = FeatureLeakageDetector()

    with pytest.raises(TemporalLeakageError):

        detector.validate(
            [
                "resource_quality",
                "future_click_count",
            ]
        )


def test_temporal_validation_accepts_past_features():

    detector = FeatureLeakageDetector()

    prediction_at = datetime.now(
        timezone.utc
    )

    detector.validate_temporal_features(
        {
            "historical_click_count": (
                prediction_at - timedelta(hours=1)
            )
        },
        prediction_at,
    )


def test_temporal_validation_rejects_future_features():

    detector = FeatureLeakageDetector()

    prediction_at = datetime.now(
        timezone.utc
    )

    with pytest.raises(TemporalLeakageError):

        detector.validate_temporal_features(
            {
                "historical_click_count": (
                    prediction_at + timedelta(hours=1)
                )
            },
            prediction_at,
        )


def test_naive_prediction_timestamp_is_rejected():

    detector = FeatureLeakageDetector()

    with pytest.raises(ValueError):

        detector.validate_temporal_features(
            {},
            datetime.now(),
        )


def test_naive_feature_timestamp_is_rejected():

    detector = FeatureLeakageDetector()

    with pytest.raises(ValueError):

        detector.validate_temporal_features(
            {
                "historical_click_count": datetime.now()
            },
            datetime.now(timezone.utc),
        )


def test_duplicate_feature_names_are_rejected():

    detector = FeatureLeakageDetector()

    with pytest.raises(ValueError):

        detector.inspect(
            [
                "resource_quality",
                "resource_quality",
            ]
        )