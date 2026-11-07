from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from app.services.opportunities.ranking.exceptions import (
    OpportunityQualityError,
)


@dataclass(frozen=True)
class QualityEvaluation:
    score: float
    description_score: float
    official_url_score: float
    organizer_score: float
    deadline_score: float
    eligibility_score: float
    skills_score: float
    provenance_score: float
    reasons: tuple[str, ...]


class OpportunityQualityAssessor:
    """
    Evaluates opportunity information completeness.

    The score measures metadata completeness, not authenticity
    or independent verification.

    Maximum score: 100.
    """

    WEIGHTS = {
        "description": 20.0,
        "official_url": 20.0,
        "organizer": 15.0,
        "deadline": 15.0,
        "eligibility": 10.0,
        "skills": 10.0,
        "provenance": 10.0,
    }

    def evaluate(
        self,
        opportunity: dict[str, Any],
    ) -> QualityEvaluation:

        if not isinstance(opportunity, dict):
            raise OpportunityQualityError(
                "Opportunity must be a dictionary."
            )

        self._validate_opportunity(opportunity)

        description_score = self._description_score(
            opportunity.get("description")
        )

        official_url_score = self._url_score(
            opportunity.get("official_url")
        )

        organizer_score = self._presence_score(
            opportunity.get("organizer")
        )

        deadline_score = self._deadline_score(opportunity)

        eligibility_score = self._eligibility_score(
            opportunity.get("eligibility")
        )

        skills_score = self._skills_score(
            opportunity.get("required_skills")
        )

        provenance_score = self._provenance_score(opportunity)

        components = {
            "description": description_score,
            "official_url": official_url_score,
            "organizer": organizer_score,
            "deadline": deadline_score,
            "eligibility": eligibility_score,
            "skills": skills_score,
            "provenance": provenance_score,
        }

        total_score = sum(
            components[name] * self.WEIGHTS[name] / 100
            for name in components
        )

        reasons = tuple(
            f"{name.replace('_', ' ').title()}: {score:.1f}/100"
            for name, score in components.items()
        )

        return QualityEvaluation(
            score=round(total_score, 2),
            description_score=description_score,
            official_url_score=official_url_score,
            organizer_score=organizer_score,
            deadline_score=deadline_score,
            eligibility_score=eligibility_score,
            skills_score=skills_score,
            provenance_score=provenance_score,
            reasons=reasons,
        )

    @staticmethod
    def _validate_opportunity(
        opportunity: dict[str, Any],
    ) -> None:

        description = opportunity.get("description")

        if description is not None and not isinstance(description, str):
            raise OpportunityQualityError(
                "Description must be a string or None."
            )

        eligibility = opportunity.get("eligibility")

        if eligibility is not None and not isinstance(eligibility, dict):
            raise OpportunityQualityError(
                "Eligibility must be a dictionary or None."
            )

        skills = opportunity.get("required_skills")

        if skills is not None:
            if not isinstance(skills, list):
                raise OpportunityQualityError(
                    "Required skills must be a list or None."
                )

            if not all(
                isinstance(skill, str) and skill.strip()
                for skill in skills
            ):
                raise OpportunityQualityError(
                    "Every required skill must be a non-empty string."
                )

    @staticmethod
    def _description_score(
        description: str | None,
    ) -> float:

        if not isinstance(description, str) or not description.strip():
            return 0.0

        cleaned = description.strip()
        character_count = len(cleaned)
        word_count = len(cleaned.split())

        if character_count >= 250 or word_count >= 40:
            return 100.0

        if character_count >= 150:
            return 85.0

        if character_count >= 50:
            return 60.0

        return 25.0

    @staticmethod
    def _url_score(url: str | None) -> float:

        if not isinstance(url, str) or not url.strip():
            return 0.0

        try:
            parsed = urlsplit(url.strip())

            if parsed.scheme not in {"http", "https"}:
                return 0.0

            if not parsed.hostname:
                return 0.0

            if parsed.username or parsed.password:
                return 0.0

            _ = parsed.port

            return 100.0

        except ValueError:
            return 0.0

    @staticmethod
    def _presence_score(value: Any) -> float:

        if value is None:
            return 0.0

        if isinstance(value, str):
            return 100.0 if value.strip() else 0.0

        return 100.0 if value else 0.0

    @staticmethod
    def _deadline_score(
        opportunity: dict[str, Any],
    ) -> float:

        registration_start = opportunity.get("registration_start")
        registration_deadline = opportunity.get(
            "registration_deadline"
        )

        if registration_deadline is not None:
            return 100.0

        if registration_start is not None:
            return 50.0

        return 0.0

    @staticmethod
    def _eligibility_score(
        eligibility: dict | None,
    ) -> float:

        if not eligibility:
            return 0.0

        return 100.0

    @staticmethod
    def _skills_score(
        skills: list | None,
    ) -> float:

        if not skills:
            return 0.0

        return 100.0

    @staticmethod
    def _provenance_score(
        opportunity: dict[str, Any],
    ) -> float:

        source_url = opportunity.get("source_url")
        provider = opportunity.get("provider")
        external_id = opportunity.get("external_id")

        metadata = opportunity.get(
            "opportunity_metadata",
            opportunity.get("metadata"),
        )

        metadata_sources = []

        if isinstance(metadata, dict):
            sources = metadata.get("sources", [])

            if isinstance(sources, list):
                metadata_sources = [
                    source
                    for source in sources
                    if isinstance(source, str) and source.strip()
                ]

        has_source_url = (
            isinstance(source_url, str)
            and bool(source_url.strip())
        )

        has_provider = (
            isinstance(provider, str)
            and bool(provider.strip())
        )

        has_external_id = (
            isinstance(external_id, str)
            and bool(external_id.strip())
        )

        provenance_signals = (
            has_source_url,
            has_provider,
            has_external_id,
            bool(metadata_sources),
        )

        return (
            sum(provenance_signals)
            / len(provenance_signals)
            * 100.0
        )