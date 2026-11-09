from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping
from uuid import UUID


class FilteringError(ValueError):
    """Base exception for hybrid filtering errors."""


class EligibilityStatus(str, Enum):
    VERIFIED = "verified"
    UNKNOWN = "unknown"
    FAILED = "failed"


class AvailabilityStatus(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


class UnknownEligibilityPolicy(str, Enum):
    EXCLUDE = "exclude"
    ALLOW_WITH_WARNING = "allow_with_warning"


@dataclass(frozen=True, slots=True)
class EligibilityDecision:
    """
    Explicit validity and eligibility information.

    None represents unknown information. It must not be
    silently interpreted as True.
    """

    resource_id: UUID

    is_valid: bool | None

    is_eligible: bool | None

    availability: AvailabilityStatus

    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.resource_id, UUID):
            raise FilteringError(
                "resource_id must be a UUID."
            )

        for name, value in (
            ("is_valid", self.is_valid),
            ("is_eligible", self.is_eligible),
        ):
            if value is not None and not isinstance(value, bool):
                raise FilteringError(
                    f"{name} must be bool or None."
                )

        if not isinstance(
            self.availability,
            AvailabilityStatus,
        ):
            raise FilteringError(
                "Invalid availability status."
            )

        if not isinstance(self.reasons, tuple):
            raise FilteringError(
                "reasons must be a tuple."
            )

        if any(
            not isinstance(reason, str) or not reason.strip()
            for reason in self.reasons
        ):
            raise FilteringError(
                "Every exclusion reason must be a non-empty string."
            )


@dataclass(frozen=True, slots=True)
class FilteringResult:
    resource_id: UUID

    accepted: bool

    exclusion_reasons: tuple[str, ...]

    warnings: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.accepted and self.exclusion_reasons:
            raise FilteringError(
                "Accepted resources cannot have exclusion reasons."
            )

        if not self.accepted and not self.exclusion_reasons:
            raise FilteringError(
                "Rejected resources require an exclusion reason."
            )


class HybridEligibilityFilter:
    """
    Applies hard validity, eligibility and availability rules.

    Scores are intentionally not accepted by this service.
    """

    def __init__(
        self,
        unknown_policy: UnknownEligibilityPolicy = (
            UnknownEligibilityPolicy.EXCLUDE
        ),
    ) -> None:

        if not isinstance(
            unknown_policy,
            UnknownEligibilityPolicy,
        ):
            raise FilteringError(
                "Invalid unknown eligibility policy."
            )

        self._unknown_policy = unknown_policy

    def evaluate(
        self,
        decision: EligibilityDecision,
    ) -> FilteringResult:

        if not isinstance(
            decision,
            EligibilityDecision,
        ):
            raise FilteringError(
                "decision must be an EligibilityDecision."
            )

        exclusions = list(decision.reasons)
        warnings: list[str] = []

        if decision.is_valid is False:
            exclusions.append("resource_invalid")

        elif decision.is_valid is None:
            self._handle_unknown(
                "resource_validity_unknown",
                exclusions,
                warnings,
            )

        if decision.is_eligible is False:
            exclusions.append("user_not_eligible")

        elif decision.is_eligible is None:
            self._handle_unknown(
                "eligibility_unknown",
                exclusions,
                warnings,
            )

        if decision.availability == AvailabilityStatus.UNAVAILABLE:
            exclusions.append("resource_unavailable")

        elif decision.availability == AvailabilityStatus.EXPIRED:
            exclusions.append("resource_expired")

        elif decision.availability == AvailabilityStatus.UNKNOWN:
            self._handle_unknown(
                "availability_unknown",
                exclusions,
                warnings,
            )

        # Remove duplicate reasons while preserving order.
        exclusions = list(dict.fromkeys(exclusions))

        return FilteringResult(
            resource_id=decision.resource_id,
            accepted=not exclusions,
            exclusion_reasons=tuple(exclusions),
            warnings=tuple(warnings),
        )

    def _handle_unknown(
        self,
        reason: str,
        exclusions: list[str],
        warnings: list[str],
    ) -> None:

        if (
            self._unknown_policy
            == UnknownEligibilityPolicy.EXCLUDE
        ):
            exclusions.append(reason)

        else:
            warnings.append(reason)


class HybridFilteringPipeline:
    """
    Applies eligibility decisions to a collection of candidates.

    Every candidate must have an explicit decision. This avoids
    silently treating missing validation data as verified.
    """

    def __init__(
        self,
        eligibility_filter: HybridEligibilityFilter,
    ) -> None:

        if not isinstance(
            eligibility_filter,
            HybridEligibilityFilter,
        ):
            raise FilteringError(
                "eligibility_filter has an invalid type."
            )

        self._filter = eligibility_filter

    def execute(
        self,
        resource_ids: tuple[UUID, ...],
        decisions: Mapping[UUID, EligibilityDecision],
    ) -> tuple[FilteringResult, ...]:

        if not isinstance(resource_ids, tuple):
            raise FilteringError(
                "resource_ids must be a tuple."
            )

        if not isinstance(decisions, Mapping):
            raise FilteringError(
                "decisions must be a mapping."
            )

        if len(set(resource_ids)) != len(resource_ids):
            raise FilteringError(
                "resource_ids must not contain duplicates."
            )

        results = []

        for resource_id in resource_ids:

            if not isinstance(resource_id, UUID):
                raise FilteringError(
                    "Every resource ID must be a UUID."
                )

            decision = decisions.get(resource_id)

            if decision is None:
                raise FilteringError(
                    f"Missing eligibility decision for {resource_id}."
                )

            if decision.resource_id != resource_id:
                raise FilteringError(
                    "Eligibility decision resource ID mismatch."
                )

            results.append(
                self._filter.evaluate(decision)
            )

        return tuple(results)