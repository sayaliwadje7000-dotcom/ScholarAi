class ToolCallingError(Exception):
    """Base exception for the tool-calling architecture."""


class ToolRegistrationError(ToolCallingError):
    """Raised when a tool cannot be registered."""


class ToolExecutionError(ToolCallingError):
    """Raised when tool execution infrastructure fails."""


class ToolAuthorizationError(ToolCallingError):
    """Raised when a tool execution is not authorized."""