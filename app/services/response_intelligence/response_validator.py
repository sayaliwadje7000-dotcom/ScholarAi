from app.schemas.response_intelligence import (
    ResponseFormat,
)

from app.services.response_intelligence.exceptions import (
    ResponseQualityError,
)


class ResponseValidator:

    MINIMUM_RESPONSE_LENGTH = 2

    MAXIMUM_RESPONSE_LENGTH = 50000

    COMPARISON_MARKERS = (
        "difference",
        "differ",
        "different",
        "similarity",
        "similarities",
        "similar",
        "whereas",
        "while",
        "compared with",
        "compared to",
        "in contrast",
        "on the other hand",
        "|",
    )

    STEP_MARKERS = (
        "step 1",
        "step 2",
        "1.",
        "first",
        "firstly",
    )

    def validate(
        self,
        response: str,
        response_format: ResponseFormat,
    ) -> list[str]:

        # STEP 1: BASIC INPUT VALIDATION

        if not isinstance(response, str):

            raise ResponseQualityError(
                "Response must be a string."
            )

        if not response.strip():

            raise ResponseQualityError(
                "Generated response is empty."
            )

        if len(response) < self.MINIMUM_RESPONSE_LENGTH:

            raise ResponseQualityError(
                "Generated response is too short."
            )

        if len(response) > self.MAXIMUM_RESPONSE_LENGTH:

            raise ResponseQualityError(
                "Generated response exceeds the maximum length."
            )

        issues = []

        normalized_response = response.lower()

        # STEP 2: MARKDOWN CODE FENCE VALIDATION

        if response.count("```") % 2 != 0:

            issues.append(
                "Response contains an unmatched code fence."
            )

        # STEP 3: COMPARISON STRUCTURE VALIDATION

        if response_format == ResponseFormat.COMPARISON:

            has_comparison_content = any(
                marker in normalized_response
                for marker in self.COMPARISON_MARKERS
            )

            if not has_comparison_content:

                issues.append(
                    "Comparison response does not contain "
                    "an identifiable comparison structure."
                )

        # STEP 4: STEP-BY-STEP STRUCTURE VALIDATION

        if response_format == ResponseFormat.STEP_BY_STEP:

            has_steps = any(
                marker in normalized_response
                for marker in self.STEP_MARKERS
            )

            if not has_steps:

                issues.append(
                    "Step-by-step response does not contain "
                    "an identifiable sequence."
                )

        return issues