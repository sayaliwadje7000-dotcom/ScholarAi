"""Privacy and leakage-prevention exceptions."""


class PrivacyError(Exception):
    """Base exception for privacy-related failures."""


class SensitiveDataError(PrivacyError):
    """Raised when sensitive data is detected."""


class IdentifierLeakageError(PrivacyError):
    """Raised when identifiers enter model features."""


class TargetLeakageError(PrivacyError):
    """Raised when target information enters model features."""


class TemporalLeakageError(PrivacyError):
    """Raised when future information enters historical features."""


class DatasetPrivacyError(PrivacyError):
    """Raised when a dataset violates privacy requirements."""


class MetadataSanitizationError(PrivacyError):
    """Raised when metadata cannot be safely sanitized."""