from copy import deepcopy
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.services.opportunities.normalization.url_normalizer import (
    OpportunityURLNormalizer,
)


class OpportunityNormalizer:
    """
    Converts opportunity records into a normalized dictionary.

    Supports:
    - Dictionaries.
    - Pydantic models.
    - Objects exposing __dict__.

    Missing information is not fabricated.
    """

    REQUIRED_FIELDS = (
        "provider",
        "title",
        "opportunity_type",
    )

    STRING_FIELDS = (
        "description",
        "organizer",
        "location",
    )

    URL_FIELDS = (
        "official_url",
        "source_url",
        "application_url",
    )

    @staticmethod
    def _convert_enum(value):
        if isinstance(value, Enum):
            return value.value

        return value

    @classmethod
    def _to_dict(cls, opportunity: Any) -> dict:

        if isinstance(opportunity, dict):
            data = deepcopy(opportunity)

        elif hasattr(opportunity, "model_dump"):
            data = opportunity.model_dump(mode="python")

        elif hasattr(opportunity, "__dict__"):
            data = deepcopy(vars(opportunity))

        else:
            raise TypeError(
                "Opportunity must be a dictionary or model object."
            )

        return {
            key: cls._convert_enum(value)
            for key, value in data.items()
        }

    @classmethod
    def normalize(cls, opportunity: Any) -> dict:

        data = cls._to_dict(opportunity)

        # Required fields
        for field in cls.REQUIRED_FIELDS:

            value = data.get(field)

            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"Opportunity field '{field}' is required."
                )

            data[field] = value.strip()

        # Provider normalization
        data["provider"] = data["provider"].casefold()

        # Title normalization
        data["title"] = " ".join(data["title"].split())

        # Opportunity type normalization
        data["opportunity_type"] = (
            data["opportunity_type"].casefold()
        )

        # Optional string normalization
        for field in cls.STRING_FIELDS:

            value = data.get(field)

            if value is not None:

                if not isinstance(value, str):
                    raise TypeError(
                        f"{field} must be a string or None."
                    )

                data[field] = value.strip() or None

        # URL normalization
        for field in cls.URL_FIELDS:

            value = data.get(field)

            if value is None:
                data[field] = None

            elif isinstance(value, str):

                data[field] = (
                    OpportunityURLNormalizer.normalize(value)
                    if value.strip()
                    else None
                )

            else:
                raise TypeError(
                    f"{field} must be a string or None."
                )

        # Eligibility normalization
        eligibility = data.get("eligibility")

        if eligibility is None:
            eligibility = {}

        if not isinstance(eligibility, dict):
            raise TypeError(
                "Eligibility must be a dictionary."
            )

        data["eligibility"] = deepcopy(eligibility)

        # Required skills normalization
        skills = data.get("required_skills")

        if skills is None:
            skills = []

        if not isinstance(skills, list):
            raise TypeError(
                "Required skills must be a list."
            )

        normalized_skills = []
        seen_skills = set()

        for skill in skills:

            if not isinstance(skill, str):
                raise TypeError(
                    "Every required skill must be a string."
                )

            skill = skill.strip()

            if not skill:
                continue

            key = skill.casefold()

            if key not in seen_skills:
                seen_skills.add(key)
                normalized_skills.append(skill)

        data["required_skills"] = normalized_skills

        # Metadata compatibility
        metadata = data.get("metadata")

        if metadata is None:
            metadata = data.get(
                "opportunity_metadata",
                {},
            )

        if not isinstance(metadata, dict):
            raise TypeError(
                "Opportunity metadata must be a dictionary."
            )

        data["metadata"] = deepcopy(metadata)

        data.pop("opportunity_metadata", None)

        # Retrieval timestamp
        if data.get("retrieved_at") is None:
            data["retrieved_at"] = datetime.now(timezone.utc)

        return data

    @classmethod
    def normalize_many(
        cls,
        opportunities: list[Any],
    ) -> list[dict]:

        if not isinstance(opportunities, list):
            raise TypeError(
                "Expected a list of opportunities."
            )

        return [
            cls.normalize(item)
            for item in opportunities
        ]