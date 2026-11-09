from app.schemas.response_intelligence import (
    ResponseFormat,
    ResponseIntelligenceRequest,
    ResponseIntelligenceResult,
    ResponseValidationStatus,
)

from app.services.response_intelligence.response_parser import (
    ResponseParser,
)

from app.services.response_intelligence.response_normalizer import (
    ResponseNormalizer,
)

from app.services.response_intelligence.response_validator import (
    ResponseValidator,
)

from app.services.response_intelligence.exceptions import (
    ResponseSafetyError,
)

from app.services.safety_service import validate_output


class ResponseIntelligenceService:

    def __init__(
        self,
        parser: ResponseParser | None = None,
        normalizer: ResponseNormalizer | None = None,
        validator: ResponseValidator | None = None,
    ):
        self.parser = parser or ResponseParser()
        self.normalizer = normalizer or ResponseNormalizer()
        self.validator = validator or ResponseValidator()

    def process(
        self,
        request: ResponseIntelligenceRequest,
    ) -> ResponseIntelligenceResult:

        # STEP 1: NORMALIZE

        normalized_response = self.normalizer.normalize(
            request.response
        )

        structured_response = None

        # STEP 2: PROCESS RESPONSE FORMAT

        if request.response_format == ResponseFormat.PLAIN_TEXT:

            final_response = normalized_response

        elif request.response_format == ResponseFormat.ACADEMIC:

            # Academic structured responses must contain valid JSON.
            structured_response = self.parser.parse(
                normalized_response
            )

            final_response = self._format_structured_response(
                structured_response,
                request.response_format,
            )

        else:

            # Comparison, summary and step-by-step responses
            # may be ordinary text or structured JSON.
            # Parse only when the response appears to contain JSON.

            stripped_response = normalized_response.lstrip()

            if stripped_response.startswith(("{", "```")):

                structured_response = self.parser.parse(
                    normalized_response
                )

                final_response = self._format_structured_response(
                    structured_response,
                    request.response_format,
                )

            else:

                final_response = normalized_response

        # STEP 3: QUALITY VALIDATION

        quality_issues = self.validator.validate(
            final_response,
            request.response_format,
        )

        # STEP 4: SAFETY VALIDATION

        safety_validated = False

        if request.validate_safety:

            safety_result = validate_output(final_response)

            if not safety_result.allowed:
                raise ResponseSafetyError(
                    "Generated response failed output safety validation."
                )

            safety_validated = True

        # STEP 5: VALIDATION STATUS

        validation_status = (
            ResponseValidationStatus.PARTIALLY_VALID
            if quality_issues
            else ResponseValidationStatus.VALID
        )

        # STEP 6: BUILD RESULT

        return ResponseIntelligenceResult(
            response=final_response,
            response_format=request.response_format,
            validation_status=validation_status,
            structured_response=structured_response,
            quality_issues=quality_issues,
            safety_validated=safety_validated,
            character_count=len(final_response),
            word_count=len(final_response.split()),
        )

    @staticmethod
    def _format_structured_response(
        structured_response,
        response_format: ResponseFormat,
    ) -> str:

        sections = [
            structured_response.answer
        ]

        if structured_response.key_points:
            sections.append(
                "## Key Points\n"
                + "\n".join(
                    f"- {point}"
                    for point in structured_response.key_points
                )
            )

        if structured_response.examples:
            sections.append(
                "## Examples\n"
                + "\n".join(
                    f"- {example}"
                    for example in structured_response.examples
                )
            )

        if structured_response.caveats:
            sections.append(
                "## Important Notes\n"
                + "\n".join(
                    f"- {caveat}"
                    for caveat in structured_response.caveats
                )
            )

        if structured_response.conclusion:
            sections.append(
                "## Conclusion\n"
                + structured_response.conclusion
            )

        return "\n\n".join(sections)


response_intelligence_service = ResponseIntelligenceService()