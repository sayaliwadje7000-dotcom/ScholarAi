"""Privacy configuration for ScholarAI recommendation ML."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PrivacyConfig:
    """Centralized privacy and data-protection policies."""

    reject_identifier_features: bool = True

    reject_sensitive_features: bool = True

    reject_target_leakage: bool = True

    require_user_separated_validation: bool = True

    require_temporal_feature_validation: bool = True

    redact_pii_from_metadata: bool = True

    allow_raw_user_identifiers_in_audit_records: bool = False

    allow_raw_resource_identifiers_in_audit_records: bool = False

    minimum_dataset_samples: int = 10

    minimum_distinct_users: int = 4

    maximum_metadata_string_length: int = 1000

    def __post_init__(self) -> None:

        if self.minimum_dataset_samples < 1:
            raise ValueError(
                "minimum_dataset_samples must be positive."
            )

        if self.minimum_distinct_users < 2:
            raise ValueError(
                "minimum_distinct_users must be at least 2."
            )

        if self.maximum_metadata_string_length < 1:
            raise ValueError(
                "maximum_metadata_string_length must be positive."
            )