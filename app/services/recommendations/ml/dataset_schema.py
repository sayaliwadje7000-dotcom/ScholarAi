"""Versioned, privacy-conscious schema for recommendation training rows."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import IntEnum, StrEnum
from typing import Any
from uuid import UUID


DATASET_SCHEMA_VERSION = "1.0"


class DatasetLabel(IntEnum):
    """Relevance labels used by recommendation experiments."""

    NOT_RELEVANT = 0
    RELEVANT = 1


class LabelSource(StrEnum):
    INTERACTION = "interaction"
    EXPLICIT_FEEDBACK = "explicit_feedback"


@dataclass(frozen=True, slots=True)
class RecommendationTrainingExample:
    """One observed user-resource relevance judgment."""

    user_id: UUID
    resource_id: UUID
    label: DatasetLabel
    label_source: LabelSource
    source_event: str
    observed_at: datetime

    schema_version: str = DATASET_SCHEMA_VERSION
    confidence: float = 1.0

    def __post_init__(self) -> None:

        if not isinstance(self.user_id, UUID):
            raise TypeError("user_id must be a UUID grouping key")

        if not isinstance(self.resource_id, UUID):
            raise TypeError("resource_id must be a UUID grouping key")

        if not isinstance(self.label, DatasetLabel):
            raise TypeError("label must be a DatasetLabel")

        if not isinstance(self.label_source, LabelSource):
            raise TypeError("label_source must be a LabelSource")

        if not self.source_event or not self.source_event.strip():
            raise ValueError("source_event must be a non-empty string")

        if (
            self.observed_at.tzinfo is None
            or self.observed_at.utcoffset() is None
        ):
            raise ValueError(
                "observed_at must be timezone-aware"
            )

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "confidence must be between 0 and 1"
            )

        if self.schema_version != DATASET_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported dataset schema version: "
                f"{self.schema_version}"
            )

    @property
    def sample_key(self) -> tuple[UUID, UUID]:
        """Stable key for user-resource grouping."""

        return self.user_id, self.resource_id

    def to_model_record(self) -> dict[str, Any]:
        """Return model-facing data without direct grouping identifiers."""

        return {
            "label": int(self.label),
            "label_source": self.label_source.value,
            "source_event": self.source_event,
            "observed_at": (
                self.observed_at
                .astimezone(timezone.utc)
                .isoformat()
            ),
            "confidence": self.confidence,
            "schema_version": self.schema_version,
        }

    def to_audit_record(self) -> dict[str, Any]:
        """Return internal audit information."""

        record = asdict(self)

        record["label"] = int(self.label)
        record["label_source"] = self.label_source.value
        record["user_id"] = str(self.user_id)
        record["resource_id"] = str(self.resource_id)
        record["observed_at"] = self.observed_at.isoformat()

        return record