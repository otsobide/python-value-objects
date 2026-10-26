"""Core machinery shared by every value object."""

from __future__ import annotations

__all__ = [
    "CurrencyMismatchError",
    "InvalidFormatError",
    "InvalidTypeError",
    "OutOfRangeError",
    "PrecisionError",
    "ValueObjectError",
]


# ----------------------------------------------------------------------------------------------- errors


def show(value: object) -> str:
    """repr() truncated to 80 characters, for error messages."""
    text = repr(value)
    return text if len(text) <= 80 else f"{text[:77]}..."


class ValueObjectError(ValueError):
    """Base class of every validation error raised by pyvalueobjects.

    ``str(err)`` is ``"<Class>: <reason>"``; ``.reason`` is the message without the class name,
    ``.vo`` the value-object class and ``.value`` the offending input.
    """

    def __init__(self, reason: str, *, vo: type | None = None, value: object = None) -> None:
        super().__init__(f"{vo.__name__}: {reason}" if vo is not None else reason)
        self.reason = reason
        self.vo = vo
        self.value = value


class InvalidTypeError(ValueObjectError, TypeError):
    """The raw input has a Python type the value object does not accept."""


class InvalidFormatError(ValueObjectError):
    """The raw input has an accepted type but cannot be parsed, or breaks a format rule."""


class PrecisionError(InvalidFormatError):
    """The value is finer than the value object can hold (decimal places, whole days)."""


class OutOfRangeError(ValueObjectError):
    """A bound (gt/ge/lt/le), a length limit or an ordering invariant (start <= end) is violated."""


class CurrencyMismatchError(ValueObjectError):
    """An operation combined Money values in different currencies."""
