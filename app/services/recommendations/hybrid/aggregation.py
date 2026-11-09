from __future__ import annotations

import re

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable
from urllib.parse import (
    parse_qsl,
    urlencode,
    urlsplit,
    urlunsplit,
)

from app.services.recommendations.hybrid.contracts import (
    ComponentScore,
    ComponentStatus,
    HybridCandidate,
    RecommendationComponent,
    RecommendationProvenance,
)


class CandidateAggregationError(ValueError):
    """Base exception for candidate aggregation failures."""


class CandidateIdentityError(CandidateAggregationError):
    """Raised when a candidate has an invalid identity."""


class CandidateScoreConflictError(CandidateAggregationError):
    """Raised when component scores conflict."""


class CandidateMetadataError(CandidateAggregationError):
    """Raised when candidate metadata cannot be merged."""


@dataclass(frozen=True, slots=True)
class CandidateAggregationResult:
    """
    Result of combining and deduplicating hybrid candidates.

    candidates:
        Final unique candidate collection.

    input_count:
        Number of candidates supplied.

    output_count:
        Number of unique candidates after aggregation.

    duplicate_count:
        Number of duplicate candidates merged.
    """

    candidates: tuple[HybridCandidate, ...]

    input_count: int

    output_count: int

    duplicate_count: int

    def __post_init__(self) -> None:
        if self.input_count < 0:
            raise CandidateAggregationError(
                "input_count cannot be negative."
            )

        if self.output_count < 0:
            raise CandidateAggregationError(
                "output_count cannot be negative."
            )

        if self.duplicate_count < 0:
            raise CandidateAggregationError(
                "duplicate_count cannot be negative."
            )

        if self.input_count != (
            self.output_count + self.duplicate_count
        ):
            raise CandidateAggregationError(
                "Aggregation counts are inconsistent."
            )

        if len(self.candidates) != self.output_count:
            raise CandidateAggregationError(
                "output_count does not match candidate collection."
            )


class CandidateURLNormalizer:
    """
    Produces a canonical URL for duplicate detection.

    Normalization includes:

    - Lowercase scheme and hostname.
    - Removal of default HTTP/HTTPS ports.
    - Removal of URL fragments.
    - Removal of common tracking parameters.
    - Deterministic query parameter ordering.
    - Removal of trailing path slashes.
    - Preservation of meaningful path and query information.

    The original URL is never modified in the candidate.
    """

    TRACKING_PARAMETERS = frozenset(
        {
            "fbclid",
            "gclid",
            "dclid",
            "msclkid",
            "mc_cid",
            "mc_eid",
            "ref",
            "source",
        }
    )

    TRACKING_PREFIXES = (
        "utm_",
    )

    @classmethod
    def normalize(
        cls,
        url: str | None,
    ) -> str | None:

        if url is None:
            return None

        if not isinstance(url, str):
            raise CandidateIdentityError(
                "Candidate URL must be a string or None."
            )

        value = url.strip()

        if not value:
            return None

        try:
            parsed = urlsplit(value)
        except ValueError as exc:
            raise CandidateIdentityError(
                f"Invalid candidate URL: {value!r}"
            ) from exc

        if parsed.scheme.lower() not in ("http", "https"):
            raise CandidateIdentityError(
                "Only HTTP and HTTPS URLs are supported."
            )

        if not parsed.hostname:
            raise CandidateIdentityError(
                "Candidate URL must contain a hostname."
            )

        try:
            hostname = parsed.hostname.encode(
                "idna"
            ).decode("ascii").lower()

            port = parsed.port

        except (UnicodeError, ValueError) as exc:
            raise CandidateIdentityError(
                f"Invalid URL authority: {value!r}"
            ) from exc

        scheme = parsed.scheme.lower()

        if ":" in hostname and not hostname.startswith("["):
            hostname = f"[{hostname}]"

        if port is not None:
            if not (
                (scheme == "http" and port == 80)
                or
                (scheme == "https" and port == 443)
            ):
                netloc = f"{hostname}:{port}"
            else:
                netloc = hostname
        else:
            netloc = hostname

        path = re.sub(
            r"/+",
            "/",
            parsed.path,
        )

        if path != "/":
            path = path.rstrip("/")

        query_parameters = []

        for key, parameter_value in parse_qsl(
            parsed.query,
            keep_blank_values=True,
        ):

            normalized_key = key.lower()

            if normalized_key in cls.TRACKING_PARAMETERS:
                continue

            if any(
                normalized_key.startswith(prefix)
                for prefix in cls.TRACKING_PREFIXES
            ):
                continue

            query_parameters.append(
                (key, parameter_value)
            )

        query_parameters.sort(
            key=lambda item: (
                item[0].lower(),
                item[1],
            )
        )

        query = urlencode(
            query_parameters,
            doseq=True,
        )

        return urlunsplit(
            (
                scheme,
                netloc,
                path,
                query,
                "",
            )
        )


class CandidateIdentityResolver:
    """
    Generates stable identity keys for candidate deduplication.

    Two candidates are considered equivalent when they share:

    1. The same resource UUID, or
    2. The same canonical HTTP/HTTPS URL.

    UUID and URL matches are treated as transitive relationships.
    """

    @staticmethod
    def identity_keys(
        candidate: HybridCandidate,
    ) -> frozenset[str]:

        if not isinstance(
            candidate,
            HybridCandidate,
        ):
            raise CandidateIdentityError(
                "Expected a HybridCandidate."
            )

        keys = {
            f"uuid:{candidate.resource_id}"
        }

        canonical_url = (
            CandidateURLNormalizer.normalize(
                candidate.canonical_url
            )
        )

        if canonical_url:
            keys.add(
                f"url:{canonical_url}"
            )

        return frozenset(keys)


class _DisjointSet:
    """
    Union-find implementation used to merge transitive duplicates.

    It avoids relying on the input order to identify connected
    duplicate groups.
    """

    def __init__(
        self,
        size: int,
    ) -> None:

        self.parent = list(range(size))

        self.rank = [0] * size

    def find(
        self,
        item: int,
    ) -> int:

        if self.parent[item] != item:
            self.parent[item] = self.find(
                self.parent[item]
            )

        return self.parent[item]

    def union(
        self,
        first: int,
        second: int,
    ) -> None:

        root_first = self.find(first)

        root_second = self.find(second)

        if root_first == root_second:
            return

        if self.rank[root_first] < self.rank[root_second]:
            root_first, root_second = (
                root_second,
                root_first,
            )

        self.parent[root_second] = root_first

        if self.rank[root_first] == self.rank[root_second]:
            self.rank[root_first] += 1


class CandidateScoreMerger:
    """
    Merges component scores from duplicate candidate records.

    Rules:

    - An available score is preferred over an unavailable score.
    - An available score is preferred over a failed score.
    - Conflicting available scores from the same component
      are rejected instead of silently choosing one.
    - Missing scores are never replaced with zero.
    """

    STATUS_PRIORITY = {
        ComponentStatus.AVAILABLE: 4,
        ComponentStatus.FAILED: 3,
        ComponentStatus.UNAVAILABLE: 2,
        ComponentStatus.NOT_APPLICABLE: 1,
    }

    @classmethod
    def merge(
        cls,
        candidates: tuple[HybridCandidate, ...],
    ) -> tuple[ComponentScore, ...]:

        selected: dict[
            RecommendationComponent,
            ComponentScore,
        ] = {}

        for candidate in candidates:

            for score in candidate.component_scores:

                existing = selected.get(
                    score.component
                )

                if existing is None:
                    selected[score.component] = score
                    continue

                cls._merge_one(
                    selected,
                    score,
                    existing,
                )

        return tuple(
            selected[component]
            for component in sorted(
                selected,
                key=lambda item: item.value,
            )
        )

    @classmethod
    def _merge_one(
        cls,
        selected: dict[
            RecommendationComponent,
            ComponentScore,
        ],
        incoming: ComponentScore,
        existing: ComponentScore,
    ) -> None:

        existing_priority = cls.STATUS_PRIORITY[
            existing.status
        ]

        incoming_priority = cls.STATUS_PRIORITY[
            incoming.status
        ]

        if incoming_priority > existing_priority:
            selected[incoming.component] = incoming
            return

        if incoming_priority < existing_priority:
            return

        if incoming.status == ComponentStatus.AVAILABLE:

            if (
                incoming.value != existing.value
                or
                incoming.direction != existing.direction
            ):
                raise CandidateScoreConflictError(
                    "Conflicting available scores detected "
                    f"for component {incoming.component.value}."
                )

            return

        if (
            incoming.value != existing.value
            or
            incoming.reason != existing.reason
        ):
            raise CandidateScoreConflictError(
                "Conflicting non-available component results "
                f"detected for {incoming.component.value}."
            )


class CandidateProvenanceMerger:
    """
    Preserves unique provenance records across duplicate candidates.
    """

    @staticmethod
    def merge(
        candidates: tuple[HybridCandidate, ...],
    ) -> tuple[RecommendationProvenance, ...]:

        merged: dict[
            tuple,
            RecommendationProvenance,
        ] = {}

        for candidate in candidates:

            for provenance in candidate.provenance:

                key = (
                    provenance.component,
                    provenance.source_name,
                    provenance.source_id,
                    provenance.source_url,
                    provenance.retrieved_at,
                )

                merged[key] = provenance

        return tuple(
            merged[key]
            for key in sorted(
                merged,
                key=lambda item: tuple(
                    str(value)
                    for value in item
                ),
            )
        )


class CandidateMetadataMerger:
    """
    Merges metadata deterministically.

    The first non-conflicting value wins.

    Conflicting values are retained in a dedicated
    metadata_conflicts entry rather than silently discarded.
    """

    @staticmethod
    def merge(
        candidates: tuple[HybridCandidate, ...],
    ) -> dict:

        merged: dict = {}

        conflicts: dict[str, list] = {}

        for candidate in candidates:

            for key, value in candidate.metadata.items():

                if key not in merged:
                    merged[key] = value
                    continue

                if merged[key] == value:
                    continue

                conflict_values = conflicts.setdefault(
                    key,
                    [merged[key]],
                )

                if value not in conflict_values:
                    conflict_values.append(value)

        if conflicts:
            merged["metadata_conflicts"] = {
                key: tuple(values)
                for key, values in sorted(
                    conflicts.items()
                )
            }

        return merged


class HybridCandidateAggregator:
    """
    Aggregates candidate collections from recommendation engines.

    This class does not generate component scores.

    It merges normalized candidate records, preserves provenance,
    and removes duplicate resources.
    """

    def aggregate(
        self,
        candidate_collections: Iterable[
            Iterable[HybridCandidate]
        ],
    ) -> CandidateAggregationResult:

        if candidate_collections is None:
            raise CandidateAggregationError(
                "candidate_collections cannot be None."
            )

        candidates: list[HybridCandidate] = []

        for collection in candidate_collections:

            if collection is None:
                raise CandidateAggregationError(
                    "A candidate collection cannot be None."
                )

            for candidate in collection:

                if not isinstance(
                    candidate,
                    HybridCandidate,
                ):
                    raise CandidateAggregationError(
                        "Every candidate must be a HybridCandidate."
                    )

                candidates.append(candidate)

        input_count = len(candidates)

        if not candidates:
            return CandidateAggregationResult(
                candidates=(),
                input_count=0,
                output_count=0,
                duplicate_count=0,
            )

        groups = self._build_duplicate_groups(
            candidates
        )

        merged_candidates = []

        for group in groups:

            merged_candidates.append(
                self._merge_group(group)
            )

        merged_candidates.sort(
            key=lambda candidate: (
                candidate.title.casefold(),
                str(candidate.resource_id),
            )
        )

        output_count = len(merged_candidates)

        return CandidateAggregationResult(
            candidates=tuple(merged_candidates),
            input_count=input_count,
            output_count=output_count,
            duplicate_count=input_count - output_count,
        )

    def _build_duplicate_groups(
        self,
        candidates: list[HybridCandidate],
    ) -> list[tuple[HybridCandidate, ...]]:

        disjoint_set = _DisjointSet(
            len(candidates)
        )

        first_seen: dict[str, int] = {}

        for index, candidate in enumerate(candidates):

            keys = CandidateIdentityResolver.identity_keys(
                candidate
            )

            for key in keys:

                previous = first_seen.get(key)

                if previous is None:
                    first_seen[key] = index
                    continue

                disjoint_set.union(
                    index,
                    previous,
                )

        grouped: dict[
            int,
            list[HybridCandidate],
        ] = {}

        for index, candidate in enumerate(candidates):

            root = disjoint_set.find(index)

            grouped.setdefault(
                root,
                [],
            ).append(candidate)

        return [
            tuple(group)
            for group in grouped.values()
        ]

    def _merge_group(
        self,
        candidates: tuple[HybridCandidate, ...],
    ) -> HybridCandidate:

        if not candidates:
            raise CandidateAggregationError(
                "Cannot merge an empty candidate group."
            )

        primary = candidates[0]

        resource_ids = {
            candidate.resource_id
            for candidate in candidates
        }

        # UUID conflicts are not silently rewritten.
        # The primary UUID is retained, while URL identity
        # allows records to be merged.
        resource_id = primary.resource_id

        component_scores = CandidateScoreMerger.merge(
            candidates
        )

        provenance = CandidateProvenanceMerger.merge(
            candidates
        )

        metadata = CandidateMetadataMerger.merge(
            candidates
        )

        canonical_url = self._select_canonical_url(
            candidates
        )

        title = self._select_text(
            candidates,
            "title",
        )

        description = self._select_optional_text(
            candidates,
            "description",
        )

        resource_type = self._select_text(
            candidates,
            "resource_type",
        )

        discovered_at = self._select_earliest_datetime(
            candidates
        )

        if len(resource_ids) > 1:
            metadata["merged_resource_ids"] = tuple(
                sorted(
                    str(resource_id)
                    for resource_id in resource_ids
                )
            )

        return HybridCandidate(
            resource_id=resource_id,
            title=title,
            resource_type=resource_type,
            component_scores=component_scores,
            provenance=provenance,
            canonical_url=canonical_url,
            description=description,
            metadata=metadata,
            discovered_at=discovered_at,
        )

    @staticmethod
    def _select_text(
        candidates: tuple[HybridCandidate, ...],
        attribute: str,
    ) -> str:

        for candidate in candidates:

            value = getattr(
                candidate,
                attribute,
            )

            if isinstance(value, str) and value.strip():
                return value.strip()

        raise CandidateMetadataError(
            f"No valid {attribute} was found."
        )

    @staticmethod
    def _select_optional_text(
        candidates: tuple[HybridCandidate, ...],
        attribute: str,
    ) -> str | None:

        for candidate in candidates:

            value = getattr(
                candidate,
                attribute,
            )

            if isinstance(value, str) and value.strip():
                return value.strip()

        return None

    @staticmethod
    def _select_canonical_url(
        candidates: tuple[HybridCandidate, ...],
    ) -> str | None:

        for candidate in candidates:

            if candidate.canonical_url:
                return candidate.canonical_url.strip()

        return None

    @staticmethod
    def _select_earliest_datetime(
        candidates: tuple[HybridCandidate, ...],
    ) -> datetime | None:

        timestamps = [
            candidate.discovered_at
            for candidate in candidates
            if candidate.discovered_at is not None
        ]

        if not timestamps:
            return None

        return min(
            timestamps,
            key=lambda timestamp: timestamp.timestamp(),
        )