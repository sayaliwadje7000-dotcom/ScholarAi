"""
ScholarAI authentication exceptions.
"""


class AuthenticationError(Exception):
    """
    Raised when supplied credentials cannot authenticate
    an account.
    """

    def __init__(
        self,
        message: str = "Invalid email or password.",
    ):
        self.message = message

        super().__init__(message)