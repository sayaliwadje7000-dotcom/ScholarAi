from dataclasses import dataclass
from typing import Any

from app.services.opportunities.ranking.configuration import (
    RelevanceWeights,
)

from app.services.opportunities.ranking.exceptions import (
    OpportunityRelevanceError,
)


@dataclass(frozen=True)
class RelevanceEvaluation:
    score: float

    skills_score: float | None
    opportunity_type_score: float | None
    interests_score: float | None
    location_score: float | None
    academic_level_score: float | None
    query_score: float | None

    evaluated_weight: float
    matched_signals: tuple[str, ...]
    reasons: tuple[str, ...]


class OpportunityRelevanceScorer:
    """
    Calculates deterministic student-opportunity relevance.

    Only available personalization signals contribute to the
    normalized relevance score.
    """

    def __init__(
        self,
        weights: RelevanceWeights | None = None,
    ):

        self.weights = weights or RelevanceWeights()

    @staticmethod
    def _normalize(value):

        if not isinstance(value, str):
            return ""

        return value.strip().casefold()

    @classmethod
    def _normalize_values(cls, values):

        if values is None:
            return set()

        if isinstance(values, str):
            values = [values]

        if not isinstance(values, (list, tuple, set)):
            raise OpportunityRelevanceError(
                "Expected a string or collection of strings."
            )

        return {
            cls._normalize(value)
            for value in values
            if isinstance(value, str) and value.strip()
        }

    @staticmethod
    def _overlap_score(required, available):

        if not required:
            return None

        if not available:
            return None

        return len(required.intersection(available)) / len(required) * 100

    @staticmethod
    def _text_score(text, terms):

        if not terms:
            return None

        if not isinstance(text, str) or not text.strip():
            return 0.0

        normalized_text = text.casefold()

        matched = sum(
            1
            for term in terms
            if term in normalized_text
        )

        return matched / len(terms) * 100

    def evaluate(
        self,
        opportunity: dict[str, Any],
        student_profile: dict[str, Any] | None = None,
        query: str | None = None,
    ) -> RelevanceEvaluation:

        if not isinstance(opportunity, dict):
            raise OpportunityRelevanceError(
                "opportunity must be a dictionary."
            )

        if student_profile is None:
            student_profile = {}

        if not isinstance(student_profile, dict):
            raise OpportunityRelevanceError(
                "student_profile must be a dictionary."
            )

        matched_signals = []
        reasons = []

        opportunity_skills = self._normalize_values(
            opportunity.get("required_skills")
        )

        student_skills = self._normalize_values(
            student_profile.get("skills")
        )

        skills_score = self._overlap_score(
            opportunity_skills,
            student_skills,
        )

        if skills_score is not None:
            if skills_score > 0:
                matched_signals.append("skills")
                reasons.append(
                    f"Skills match: {skills_score:.1f}%."
                )
            else:
                reasons.append("No required skills matched.")

        preferred_types = self._normalize_values(
            student_profile.get("preferred_opportunity_types")
        )

        opportunity_type = self._normalize(
            opportunity.get("opportunity_type")
        )

        opportunity_type_score = None

        if preferred_types:
            opportunity_type_score = (
                100.0
                if opportunity_type in preferred_types
                else 0.0
            )

            if opportunity_type_score:
                matched_signals.append("opportunity_type")
                reasons.append(
                    "Opportunity category matches student preference."
                )

        interests = self._normalize_values(
            student_profile.get("interests")
        )

        description = opportunity.get("description") or ""
        title = opportunity.get("title") or ""

        interests_score = self._text_score(
            f"{title} {description}",
            interests,
        )

        if interests_score is not None and interests_score > 0:
            matched_signals.append("interests")
            reasons.append(
                f"Interest match: {interests_score:.1f}%."
            )

        preferred_locations = self._normalize_values(
            student_profile.get("preferred_locations")
        )

        opportunity_location = self._normalize(
            opportunity.get("location")
        )

        location_score = None

        if preferred_locations:
            if opportunity.get("is_remote") is True:
                location_score = 100.0
            elif opportunity_location:
                location_score = (
                    100.0
                    if opportunity_location in preferred_locations
                    else 0.0
                )

            if location_score == 100.0:
                matched_signals.append("location")
                reasons.append(
                    "Opportunity location matches student preference."
                )

        academic_level_score = None

        student_year = student_profile.get("academic_year")

        eligible_years = opportunity.get(
            "eligibility",
            {},
        ).get("academic_years")

        if student_year is not None and eligible_years is not None:

            if not isinstance(eligible_years, (list, tuple, set)):
                raise OpportunityRelevanceError(
                    "eligibility.academic_years must be a collection."
                )

            academic_level_score = (
                100.0
                if student_year in eligible_years
                else 0.0
            )

            if academic_level_score:
                matched_signals.append("academic_level")
                reasons.append(
                    "Academic year matches opportunity requirements."
                )

        query_terms = self._normalize_values(
            query.split() if isinstance(query, str) else None
        )

        query_score = self._text_score(
            f"{title} {description} {opportunity.get('organizer') or ''}",
            query_terms,
        )

        if query_score is not None and query_score > 0:
            matched_signals.append("query")
            reasons.append(
                f"Search-query match: {query_score:.1f}%."
            )

        component_scores = {
            "skills": skills_score,
            "opportunity_type": opportunity_type_score,
            "interests": interests_score,
            "location": location_score,
            "academic_level": academic_level_score,
            "query": query_score,
        }

        total_weight = 0.0
        weighted_score = 0.0

        for name, score in component_scores.items():

            if score is None:
                continue

            weight = getattr(self.weights, name)

            total_weight += weight
            weighted_score += score * weight

        if total_weight > 0:
            final_score = weighted_score / total_weight
        else:
            final_score = 0.0
            reasons.append(
                "Insufficient student or query signals for personalized scoring."
            )

        return RelevanceEvaluation(
            score=round(final_score, 2),
            skills_score=skills_score,
            opportunity_type_score=opportunity_type_score,
            interests_score=interests_score,
            location_score=location_score,
            academic_level_score=academic_level_score,
            query_score=query_score,
            evaluated_weight=round(total_weight, 4),
            matched_signals=tuple(matched_signals),
            reasons=tuple(reasons),
        )