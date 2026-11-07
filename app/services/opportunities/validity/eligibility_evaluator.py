from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EligibilityEvaluation:
    status: str
    matched_criteria: tuple[str, ...]
    failed_criteria: tuple[str, ...]
    unknown_criteria: tuple[str, ...]
    reasons: tuple[str, ...]

    @property
    def is_eligible(self) -> bool:
        return self.status == "eligible"

    @property
    def is_decided(self) -> bool:
        return self.status != "unknown"


class OpportunityEligibilityEvaluator:
    """
    Evaluates opportunity eligibility against a student profile.

    Missing profile information is treated as unknown.
    Missing opportunity restrictions are not treated as failures.
    """

    def evaluate(
        self,
        eligibility: dict[str, Any] | None,
        student_profile: dict[str, Any] | None,
    ) -> EligibilityEvaluation:

        if eligibility is None:
            eligibility = {}

        if student_profile is None:
            student_profile = {}

        if not isinstance(eligibility, dict):
            raise ValueError("eligibility must be a dictionary")

        if not isinstance(student_profile, dict):
            raise ValueError("student_profile must be a dictionary")

        matched = []
        failed = []
        unknown = []
        reasons = []

        self._evaluate_list_criteria(
            eligibility,
            student_profile,
            "academic_years",
            "academic_year",
            matched,
            failed,
            unknown,
            reasons,
        )

        self._evaluate_list_criteria(
            eligibility,
            student_profile,
            "branches",
            "branch",
            matched,
            failed,
            unknown,
            reasons,
        )

        self._evaluate_list_criteria(
            eligibility,
            student_profile,
            "countries",
            "country",
            matched,
            failed,
            unknown,
            reasons,
        )

        self._evaluate_list_criteria(
            eligibility,
            student_profile,
            "graduation_years",
            "graduation_year",
            matched,
            failed,
            unknown,
            reasons,
        )

        self._evaluate_list_criteria(
            eligibility,
            student_profile,
            "qualifications",
            "qualification",
            matched,
            failed,
            unknown,
            reasons,
        )

        self._evaluate_list_criteria(
            eligibility,
            student_profile,
            "citizenships",
            "citizenship",
            matched,
            failed,
            unknown,
            reasons,
        )

        self._evaluate_list_criteria(
            eligibility,
            student_profile,
            "locations",
            "location",
            matched,
            failed,
            unknown,
            reasons,
        )

        self._evaluate_numeric_range(
            eligibility,
            student_profile,
            "min_year",
            "max_year",
            "academic_year",
            "academic_year_range",
            matched,
            failed,
            unknown,
            reasons,
        )

        self._evaluate_numeric_range(
            eligibility,
            student_profile,
            "age_min",
            "age_max",
            "age",
            "age_range",
            matched,
            failed,
            unknown,
            reasons,
        )

        self._evaluate_required_skills(
            eligibility,
            student_profile,
            matched,
            failed,
            unknown,
            reasons,
        )

        if failed:
            status = "not_eligible"
        elif unknown:
            status = "unknown"
        else:
            status = "eligible"

        return EligibilityEvaluation(
            status=status,
            matched_criteria=tuple(matched),
            failed_criteria=tuple(failed),
            unknown_criteria=tuple(unknown),
            reasons=tuple(reasons),
        )

    @staticmethod
    def _normalize(value: Any) -> str:
        return str(value).strip().casefold()

    def _evaluate_list_criteria(
        self,
        eligibility,
        profile,
        requirement_key,
        profile_key,
        matched,
        failed,
        unknown,
        reasons,
    ):

        required = eligibility.get(requirement_key)

        if required is None:
            return

        if not isinstance(required, (list, tuple, set)):
            raise ValueError(
                f"{requirement_key} must be a list"
            )

        required_values = {
            self._normalize(value)
            for value in required
            if value is not None and str(value).strip()
        }

        if not required_values:
            return

        student_value = profile.get(profile_key)

        if student_value is None:
            unknown.append(requirement_key)
            reasons.append(
                f"Student profile is missing {profile_key}."
            )
            return

        if isinstance(student_value, (list, tuple, set)):
            student_values = {
                self._normalize(value)
                for value in student_value
            }
        else:
            student_values = {
                self._normalize(student_value)
            }

        if required_values.intersection(student_values):
            matched.append(requirement_key)
        else:
            failed.append(requirement_key)
            reasons.append(
                f"Student does not satisfy {requirement_key}."
            )

    def _evaluate_numeric_range(
        self,
        eligibility,
        profile,
        minimum_key,
        maximum_key,
        profile_key,
        result_key,
        matched,
        failed,
        unknown,
        reasons,
    ):

        minimum = eligibility.get(minimum_key)
        maximum = eligibility.get(maximum_key)

        if minimum is None and maximum is None:
            return

        student_value = profile.get(profile_key)

        if student_value is None:
            unknown.append(result_key)
            reasons.append(
                f"Student profile is missing {profile_key}."
            )
            return

        if isinstance(student_value, bool) or not isinstance(
            student_value, (int, float)
        ):
            raise ValueError(
                f"{profile_key} must be numeric"
            )

        if minimum is not None and (
            isinstance(minimum, bool)
            or not isinstance(minimum, (int, float))
        ):
            raise ValueError(
                f"{minimum_key} must be numeric"
            )

        if maximum is not None and (
            isinstance(maximum, bool)
            or not isinstance(maximum, (int, float))
        ):
            raise ValueError(
                f"{maximum_key} must be numeric"
            )

        if minimum is not None and maximum is not None:
            if minimum > maximum:
                raise ValueError(
                    f"{minimum_key} cannot exceed {maximum_key}"
                )

        if minimum is not None and student_value < minimum:
            failed.append(result_key)
            reasons.append(
                f"Student is below the required {minimum_key}."
            )
            return

        if maximum is not None and student_value > maximum:
            failed.append(result_key)
            reasons.append(
                f"Student exceeds the allowed {maximum_key}."
            )
            return

        matched.append(result_key)

    def _evaluate_required_skills(
        self,
        eligibility,
        profile,
        matched,
        failed,
        unknown,
        reasons,
    ):

        required = eligibility.get("required_skills")

        if required is None:
            return

        if not isinstance(required, (list, tuple, set)):
            raise ValueError(
                "required_skills must be a list"
            )

        required_skills = {
            self._normalize(skill)
            for skill in required
            if skill is not None and str(skill).strip()
        }

        if not required_skills:
            return

        student_skills = profile.get("skills")

        if student_skills is None:
            unknown.append("required_skills")
            reasons.append(
                "Student profile is missing skills."
            )
            return

        if not isinstance(student_skills, (list, tuple, set)):
            raise ValueError(
                "Student skills must be a list"
            )

        normalized_student_skills = {
            self._normalize(skill)
            for skill in student_skills
        }

        missing = required_skills - normalized_student_skills

        if missing:
            failed.append("required_skills")
            reasons.append(
                "Missing required skills: "
                + ", ".join(sorted(missing))
            )
        else:
            matched.append("required_skills")