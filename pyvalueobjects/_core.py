"""Core machinery shared by every value object."""

from __future__ import annotations

import operator
from abc import ABCMeta
from collections.abc import Callable
from dataclasses import FrozenInstanceError
from typing import Any, ClassVar, Self

__all__ = [
    "CurrencyMismatchError",
    "InvalidFormatError",
    "InvalidTypeError",
    "OutOfRangeError",
    "PrecisionError",
    "ValueObject",
    "ValueObjectError",
    "ValueObjectMeta",
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


# ----------------------------------------------------------------------------------------------- ValueObject


class ValueObjectMeta(ABCMeta):
    """Gives every value-object class ``__slots__ = ()`` unless it declares its own slots,
    so no instance ever has a ``__dict__``. Subclasses ABCMeta, so VOs combine with ``abc.ABC``."""

    def __new__(
        mcs, name: str, bases: tuple[type, ...], namespace: dict[str, Any], /, **kwargs: Any
    ) -> ValueObjectMeta:
        namespace.setdefault("__slots__", ())
        return super().__new__(mcs, name, bases, namespace, **kwargs)


class ValueObject(metaclass=ValueObjectMeta):
    """Immutable, slotted object, equal only to an object of the same concrete type with equal fields.

    Fields are the names in ``__slots__`` across the MRO, in declaration order; the constructor takes
    them positionally in that order. A slot ``_name`` is a private field exposed by a read-only
    property ``name`` (Scalar's ``_value`` / ``value``). From this one convention, ``repr``, pickling,
    equality, hashing, ordering and ``__match_args__`` are generic.
    """

    __slots__ = ()
    _fields: ClassVar[tuple[str, ...]] = ()
    _abstract: ClassVar[bool] = True
    __match_args__: ClassVar[tuple[str, ...]]

    def __init_subclass__(cls, *, abstract: bool = False, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls._abstract = abstract
        slots = (name for klass in reversed(cls.__mro__) for name in klass.__dict__.get("__slots__", ()))
        cls._fields = tuple(dict.fromkeys(name for name in slots if not name.startswith("__")))
        setattr(cls, "__match_args__", tuple(name.removeprefix("_") for name in cls._fields))  # noqa: B010

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError(f"{type(self).__name__} is abstract: subclass it and define __init__")

    def _set(self, **fields: object) -> None:
        """The only way to write fields: once each, from __init__. Running __init__ again on a live object raises."""
        for name, value in fields.items():
            if hasattr(self, name):
                raise FrozenInstanceError(f"cannot initialize {name!r} again: {type(self).__name__} is immutable")
            object.__setattr__(self, name, value)

    def _astuple(self) -> tuple[Any, ...]:
        return tuple(getattr(self, name) for name in self._fields)

    def _order_key(self) -> Any:
        return self._astuple()

    # equality, hashing and ordering: same concrete type only
    def __eq__(self, other: object) -> bool:
        if type(other) is not type(self):
            return NotImplemented
        return self._astuple() == other._astuple()

    def __hash__(self) -> int:
        return hash((type(self), self._astuple()))

    def _compare(self, other: object, op: Callable[[Any, Any], bool]) -> bool:
        if type(other) is not type(self):
            return NotImplemented  # type: ignore[no-any-return]
        return op(self._order_key(), other._order_key())

    def __lt__(self, other: object) -> bool:
        return self._compare(other, operator.lt)

    def __le__(self, other: object) -> bool:
        return self._compare(other, operator.le)

    def __gt__(self, other: object) -> bool:
        return self._compare(other, operator.gt)

    def __ge__(self, other: object) -> bool:
        return self._compare(other, operator.ge)

    def __bool__(self) -> bool:
        return True  # never depends on the value: `if vo:` means `if vo is not None:`

    # immutability
    def __setattr__(self, name: str, value: object) -> None:
        raise FrozenInstanceError(f"cannot assign {name!r}: {type(self).__name__} is immutable")

    def __delattr__(self, name: str) -> None:
        raise FrozenInstanceError(f"cannot delete {name!r}: {type(self).__name__} is immutable")

    # copying and pickling: immutable, so copies are the object itself; unpickling re-validates
    def __copy__(self) -> Self:
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        return self

    def __reduce__(self) -> tuple[Any, ...]:
        return (type(self), self._astuple())

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join(map(repr, self._astuple()))})"
