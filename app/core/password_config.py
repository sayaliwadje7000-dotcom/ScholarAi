"""
ScholarAI password security configuration.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PasswordSecuritySettings:

    algorithm: str = "argon2id"

    time_cost: int = 3

    memory_cost: int = 65536

    parallelism: int = 4

    hash_len: int = 32

    salt_len: int = 16

    minimum_password_length: int = 12

    maximum_password_length: int = 128

    maximum_password_bytes: int = 256


password_security_settings = PasswordSecuritySettings()