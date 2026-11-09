import json
import re

from pydantic import ValidationError

from app.schemas.response_intelligence import (
    AcademicStructuredResponse,
)

from app.services.response_intelligence.exceptions import (
    ResponseParsingError,
    ResponseValidationError,
)


class ResponseParser:

    @staticmethod
    def _extract_json(response: str) -> str:

        response = response.strip()

        fenced_match = re.fullmatch(
            r"```(?:json)?\s*(.*?)\s*```",
            response,
            flags=re.IGNORECASE | re.DOTALL,
        )

        if fenced_match:

            response = fenced_match.group(1).strip()

        if not response:

            raise ResponseParsingError(
                "Structured response is empty."
            )

        return response

    def parse(
        self,
        response: str,
    ) -> AcademicStructuredResponse:

        if not isinstance(response, str):

            raise ResponseParsingError(
                "Response must be a string."
            )

        content = self._extract_json(response)

        try:

            data = json.loads(content)

        except json.JSONDecodeError as exc:

            raise ResponseParsingError(
                "Generated response contains invalid JSON."
            ) from exc

        if not isinstance(data, dict):

            raise ResponseParsingError(
                "Structured response must be a JSON object."
            )

        try:

            return AcademicStructuredResponse.model_validate(
                data
            )

        except ValidationError as exc:

            raise ResponseValidationError(
                "Generated response does not match "
                "the academic response schema."
            ) from exc