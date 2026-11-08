"""ScholarAI recommendation ML privacy controls."""

from app.services.recommendations.ml.privacy.data_sanitizer import (
    MetadataSanitizer,
)

from app.services.recommendations.ml.privacy.dataset_privacy import (
    DatasetPrivacyReport,
    DatasetPrivacyValidator,
)

from app.services.recommendations.ml.privacy.feature_leakage import (
    FeatureLeakageDetector,
    FeatureLeakageReport,
)

from app.services.recommendations.ml.privacy.privacy_audit import (
    PrivacyAuditResult,
    RecommendationPrivacyAuditor,
)

from app.services.recommendations.ml.privacy.privacy_config import (
    PrivacyConfig,
)

from app.services.recommendations.ml.privacy.privacy_exceptions import (
    DatasetPrivacyError,
    IdentifierLeakageError,
    MetadataSanitizationError,
    PrivacyError,
    SensitiveDataError,
    TargetLeakageError,
    TemporalLeakageError,
)


__all__ = [
    "PrivacyConfig",
    "PrivacyError",
    "SensitiveDataError",
    "IdentifierLeakageError",
    "TargetLeakageError",
    "TemporalLeakageError",
    "DatasetPrivacyError",
    "MetadataSanitizationError",
    "MetadataSanitizer",
    "FeatureLeakageDetector",
    "FeatureLeakageReport",
    "DatasetPrivacyValidator",
    "DatasetPrivacyReport",
    "RecommendationPrivacyAuditor",
    "PrivacyAuditResult",
]