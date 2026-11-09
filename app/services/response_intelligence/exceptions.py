class ResponseIntelligenceError(Exception):
    """Base response-intelligence exception."""


class ResponseParsingError(ResponseIntelligenceError):
    """Generated structured response could not be parsed."""


class ResponseValidationError(ResponseIntelligenceError):
    """Generated response failed schema validation."""


class ResponseQualityError(ResponseIntelligenceError):
    """Generated response failed quality checks."""


class ResponseSafetyError(ResponseIntelligenceError):
    """Generated response failed safety validation."""