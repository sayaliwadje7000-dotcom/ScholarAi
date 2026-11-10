from collections.abc import Mapping
from typing import Any, Callable


def assert_mapping_contains(
    actual: Mapping[str, Any],
    expected: Mapping[str, Any],
) -> None:
    """
    Verify that a mapping contains the expected keys and values.

    Additional keys in the actual mapping are permitted.
    """

    for key, expected_value in expected.items():
        assert key in actual, (
            f"Expected key '{key}' was missing from mapping."
        )

        assert actual[key] == expected_value, (
            f"Unexpected value for '{key}': "
            f"expected {expected_value!r}, "
            f"received {actual[key]!r}."
        )


def assert_raises_with_message(
    exception_type: type[BaseException],
    operation: Callable[[], Any],
    expected_message: str,
) -> BaseException:
    """
    Verify exception type and message.

    This helper is intended for synchronous operations.
    """

    try:
        operation()
    except exception_type as exc:
        assert expected_message in str(exc), (
            f"Expected exception message to contain "
            f"{expected_message!r}, received {str(exc)!r}."
        )
        return exc

    except Exception as exc:
        raise AssertionError(
            f"Expected {exception_type.__name__}, "
            f"received {type(exc).__name__}."
        ) from exc

    raise AssertionError(
        f"Expected {exception_type.__name__} "
        "but no exception was raised."
    )


def normalize_text(value: str) -> str:
    """
    Normalize whitespace for text comparisons.

    This does not perform semantic similarity comparison.
    """

    if not isinstance(value, str):
        raise TypeError("Value must be a string.")

    return " ".join(value.split())
