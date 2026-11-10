"""
Authorization exceptions.
"""


class AuthorizationError(Exception):
    pass


class RoleNotFoundError(AuthorizationError):
    pass


class RoleAlreadyAssignedError(AuthorizationError):
    pass


class LastAdministratorError(AuthorizationError):
    pass
