"""Core machinery shared by every value object."""

from __future__ import annotations

import decimal
import functools
import inspect
import operator
import re
from abc import ABCMeta
from collections.abc import Callable
from dataclasses import FrozenInstanceError
from typing import Any, ClassVar, Generic, Self, TypeVar

__all__ = [
    "Bounded",
    "Bounds",
    "CurrencyMismatchError",
    "InvalidFormatError",
    "InvalidTypeError",
    "OutOfRangeError",
    "PrecisionError",
    "Scalar",
    "Sized",
    "ValueObject",
    "ValueObjectError",
    "ValueObjectMeta",
]

T = TypeVar("T")
R = TypeVar("R")
V = TypeVar("V", bound="ValueObject")
S = TypeVar("S", bound="Scalar[Any]")


# ----------------------------------------------------------------------------------------------- errors


def show(value: object) -> str:
    """repr() truncated to 80 characters, for error messages.

    An int with more digits than ``sys.get_int_max_str_digits()`` has no repr; it is shown by its
    size instead, so that building a validation error never raises a plain ValueError.
    """
    try:
        text = repr(value)
    except ValueError:
        if not isinstance(value, int):
            raise
        return f"<{'negative ' if value < 0 else ''}int with {value.bit_length()} bits>"
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


def check_range(
    vo: type,
    measured: Any,
    *,
    gt: Any = None,
    ge: Any = None,
    lt: Any = None,
    le: Any = None,
    what: str = "value",
    value: object = None,
) -> None:
    """Raise OutOfRangeError unless ``measured`` satisfies every bound that is not None."""
    for bound, holds, symbol in (
        (gt, operator.gt, ">"),
        (ge, operator.ge, ">="),
        (lt, operator.lt, "<"),
        (le, operator.le, "<="),
    ):
        if bound is not None and not holds(measured, bound):
            raise OutOfRangeError(f"{what} must be {symbol} {bound}, got {show(measured)}", vo=vo, value=value)


# ----------------------------------------------------------------------------------------------- ValueObject


def _declared_slots(klass: type) -> tuple[str, ...]:
    """The slot names a class declares itself. Python reads ``__slots__ = "name"`` as one slot, not four."""
    slots = klass.__dict__.get("__slots__", ())
    return (slots,) if isinstance(slots, str) else tuple(slots)


_signature = functools.cache(inspect.signature)  # per class, for the arity check of from_optional


class ValueObjectMeta(ABCMeta):
    """Gives every value-object class ``__slots__ = ()`` unless it declares its own slots, and refuses a
    class whose instances would still get a ``__dict__`` (a base class without ``__slots__``, or a
    ``__dict__`` slot), so no instance ever has one. Subclasses ABCMeta, so VOs combine with ``abc.ABC``."""

    def __new__(
        mcs, name: str, bases: tuple[type, ...], namespace: dict[str, Any], /, **kwargs: Any
    ) -> ValueObjectMeta:
        namespace.setdefault("__slots__", ())
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        if cls.__dictoffset__:
            raise TypeError(f"{name}: instances would have a __dict__; give every base class __slots__ = ()")
        return cls


class ValueObject(metaclass=ValueObjectMeta):
    """Immutable, slotted object, equal only to an object of the same concrete type with equal fields.

    Fields are the names in ``__slots__`` across the MRO, in declaration order; the constructor takes
    them positionally in that order. A slot ``_name`` is a private field exposed by a read-only
    property ``name`` (Scalar's ``_value`` / ``value``). From this one convention, ``repr``, pickling,
    equality, hashing, ordering, ``__match_args__`` and ``replace`` are generic.
    """

    __slots__ = ()
    _fields: ClassVar[tuple[str, ...]] = ()
    _abstract: ClassVar[bool] = True
    __match_args__: ClassVar[tuple[str, ...]]

    def __init_subclass__(cls, *, abstract: bool = False, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls._abstract = abstract
        slots = [name for klass in reversed(cls.__mro__) for name in _declared_slots(klass)]
        slots = [name for name in slots if name not in ("__dict__", "__weakref__")]
        if hidden := next((name for name in slots if name.startswith("__")), None):  # mangled or reserved
            raise TypeError(f"{cls.__name__}: slot {hidden!r} cannot be a field: a private field takes one underscore")
        cls._fields = tuple(dict.fromkeys(slots))
        match_args = tuple(name.removeprefix("_") for name in cls._fields)
        if (declared := cls.__dict__.get("__match_args__", match_args)) != match_args:  # replace() relies on it
            raise TypeError(f"{cls.__name__}: __match_args__ must be {match_args}, the fields in order, got {declared}")
        setattr(cls, "__match_args__", match_args)  # noqa: B010

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError(f"{type(self).__name__} is abstract: subclass it and define __init__")

    def _set(self, **fields: object) -> None:
        """The only way to write fields: once each, from __init__. Running __init__ again on a live object raises."""
        for name, value in fields.items():
            if hasattr(self, name):
                raise FrozenInstanceError(f"cannot initialize {name!r} again: {type(self).__name__} is immutable")
            object.__setattr__(self, name, value)

    @classmethod
    def _component(cls, name: str, kind: type[V], raw: object) -> V:
        """Coerce one constructor argument to exactly ``kind``; errors are re-raised in the name of ``cls``.

        A subclass instance (a ``Price`` given for a ``Money`` field) is rebuilt as ``kind`` from the
        fields ``kind`` declares, so stored parts are canonical and fields the subclass adds are left out.
        Scalars convert raw input; composites must be given an instance.
        """
        if type(raw) is kind:
            return raw
        try:
            if isinstance(raw, kind):
                return kind(*(getattr(raw, name) for name in kind._fields))
            if issubclass(kind, Scalar):
                return kind(raw)
        except ValueObjectError as exc:
            raise type(exc)(f"{name}: {exc.reason}", vo=cls, value=exc.value) from exc
        raise InvalidTypeError(f"{name} must be {kind.__name__}, got {type(raw).__name__}", vo=cls, value=raw)

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

    def replace(self, **changes: Any) -> Self:
        """A copy with some fields changed, re-validated: ``address.replace(city="Madrid")``."""
        if unknown := changes.keys() - set(self.__match_args__):
            raise TypeError(f"{type(self).__name__} has no field(s) {sorted(unknown)}")
        return type(self)(*(changes.get(name, getattr(self, name)) for name in self.__match_args__))

    __replace__ = replace  # copy.replace() on Python 3.13+

    # copying and pickling: immutable, so copies are the object itself; unpickling re-validates
    def __copy__(self) -> Self:
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        return self

    def __reduce__(self) -> tuple[Any, ...]:
        return (type(self), self._astuple())

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join(map(repr, self._astuple()))})"

    # optional values and validity checks, for scalars and composites alike
    @classmethod
    def from_optional(cls, *args: Any) -> Self | None:
        """None when every argument is None (a NULL column), otherwise ``cls(*args)``.

        A partially-None composite (amount without currency) is corrupt data and raises. A call that the
        constructor would refuse (a forgotten column) raises TypeError even when every argument is None."""
        if not args or any(arg is not None for arg in args):
            return cls(*args)
        try:
            _signature(cls).bind(*args)
        except TypeError as exc:
            raise TypeError(f"{cls.__name__}.from_optional(): {exc}") from None
        return None

    @classmethod
    def is_valid(cls, *args: Any) -> bool:
        """Whether ``cls(*args)`` builds; only validation errors count, misuse (wrong arity) still raises."""
        try:
            cls(*args)
        except ValueObjectError:
            return False
        return True


# ----------------------------------------------------------------------------------------------- Scalar


# Instances of subclasses of these (IntEnum, StrEnum members) are accepted as the plain type, converted by
# the base type's own method, so an overridden __int__, __float__ or __str__ cannot change the value.
_PLAIN: dict[type, Callable[[Any], Any]] = {int: int.__int__, float: float.__float__, str: str.__str__}


class Scalar(ValueObject, Generic[T], abstract=True):
    """A value object wrapping exactly one value, exposed as the read-only ``.value``.

    Pipeline: unwrap another Scalar -> ``_parse`` (type gate against ``accepts``, then ``_convert``)
    -> ``_validate`` (cooperative chain of checks and normalizations, each returning the value).
    """

    __slots__ = ("_value",)
    __match_args__ = ("value",)
    _value: T

    accepts: ClassVar[tuple[type, ...]] = ()
    _parse_str: ClassVar[staticmethod[[str], Any] | None] = None  # how from_str parses; None: the constructor takes str

    def __init__(self, value: object) -> None:
        cls = type(self)
        if cls._abstract:
            raise TypeError(f"{cls.__name__} is abstract: subclass it")
        if hasattr(self, "_value"):
            raise FrozenInstanceError(f"cannot initialize '_value' again: {cls.__name__} is immutable")
        if isinstance(value, Scalar):
            value = value._value
        object.__setattr__(self, "_value", cls._validate(cls._parse(value)))

    @property
    def value(self) -> T:
        return self._value

    def _astuple(self) -> tuple[Any, ...]:
        return (self._value,)

    @classmethod
    def _parse(cls, raw: Any) -> T:
        kind = type(raw)
        if kind not in cls.accepts:
            plain = next((t for t in _PLAIN if t in cls.accepts and isinstance(raw, t)), None)
            if plain is None or kind is bool:
                expected = " or ".join(t.__name__ for t in cls.accepts)
                raise InvalidTypeError(f"expected {expected}, got {kind.__name__}", vo=cls, value=raw)
            raw = _PLAIN[plain](raw)
        return cls._guard(cls._convert, raw)

    @classmethod
    def _convert(cls, raw: Any) -> T:
        """Turn an accepted raw input into the stored type. Plain ValueError/ArithmeticError
        raised here become InvalidFormatError."""
        return raw  # type: ignore[no-any-return]

    @classmethod
    def _validate(cls, value: T) -> T:
        """Check constraints and normalize. Overrides call ``super()._validate`` and return the value."""
        return value

    @classmethod
    def _guard(cls, func: Callable[[Any], R], raw: object) -> R:
        try:
            return func(raw)
        except ValueObjectError:
            raise
        except (ValueError, ArithmeticError) as exc:
            raise InvalidFormatError(f"cannot parse {show(raw)}", vo=cls, value=raw) from exc

    @classmethod
    def from_str(cls, text: str) -> Self:
        """Build from text; ``cls.from_str(str(x)) == x`` for every scalar except ArrayList.

        A str subclass (a StrEnum member) is read as its plain str value, as the constructor reads it."""
        if not isinstance(text, str):
            raise InvalidTypeError(f"from_str expects str, got {type(text).__name__}", vo=cls, value=text)
        text = str.__str__(text)
        return cls(text if cls._parse_str is None else cls._guard(cls._parse_str, text))

    def __str__(self) -> str:
        return str(self._value)

    def __format__(self, spec: str) -> str:
        return format(self._value, spec) if spec else str(self)

    def __repr__(self) -> str:
        shown = str(self) if str in self.accepts else self._value
        return f"{type(self).__name__}({shown!r})"


# ----------------------------------------------------------------------------------------------- constraints


class Bounds:
    """Declarative ``gt`` / ``ge`` / ``lt`` / ``le`` for anything orderable. Shared by Bounded scalars
    and composites (``class Price(Money): ge = 0``)."""

    __slots__ = ()
    gt: ClassVar[Any] = None
    ge: ClassVar[Any] = None
    lt: ClassVar[Any] = None
    le: ClassVar[Any] = None

    @classmethod
    def _check_bounds(cls, measured: Any, value: object = None) -> None:
        check_range(
            cls, measured, gt=cls.gt, ge=cls.ge, lt=cls.lt, le=cls.le, value=measured if value is None else value
        )


class Bounded(Bounds, Scalar[T], abstract=True):
    """Scalar whose value must respect gt / ge / lt / le."""

    @classmethod
    def _validate(cls, value: T) -> T:
        value = super()._validate(value)
        cls._check_bounds(value)
        return value


class Sized(Scalar[T], abstract=True):
    """Scalar whose ``len(value)`` must respect ``min_length`` / ``max_length`` (inclusive)."""

    min_length: ClassVar[int | None] = None
    max_length: ClassVar[int | None] = None

    @classmethod
    def _validate(cls, value: T) -> T:
        value = super()._validate(value)
        check_range(cls, len(value), ge=cls.min_length, le=cls.max_length, what="length", value=value)  # type: ignore[arg-type]
        return value


# ----------------------------------------------------------------------------------------------- helpers


_ASCII_WHITESPACE = " \t\n\r\f\v"


def literal(regex: re.Pattern[str], convert: Callable[[str], R]) -> Callable[[str], R]:
    """Parser for an ASCII literal: strip ASCII whitespace, ``fullmatch`` the regex (else ValueError), then ``convert``.

    Used for every non-string text format (int, decimal, ISO dates and times), so what is accepted
    never depends on how int()/float()/Decimal()/fromisoformat() behave in a given Python version:
    '1_000', '١٢', 'nan', '0x10', '20240131', 'T24:00' and a no-break space around a number are all rejected.
    """

    def parse(text: str) -> R:
        text = text.strip(_ASCII_WHITESPACE)
        if regex.fullmatch(text) is None:
            raise ValueError(f"not a valid literal: {text!r}")
        return convert(text)

    return parse


# date/timedelta/float overflow, and decimal.Overflow (an ArithmeticError) from a context that traps it
_OVERFLOW = (OverflowError, decimal.Overflow)


def _overflow(exc: ArithmeticError, vo: type, value: object) -> OutOfRangeError:
    detail = "decimal overflow" if isinstance(exc, decimal.Overflow) else exc  # str() of decimal.Overflow is cryptic
    return OutOfRangeError(f"result out of range: {detail}", vo=vo, value=value)


def binary_op(
    func: Callable[[Any, Any], Any],
    *,
    reflected: bool = False,
    operands: tuple[type, ...] | None = None,
    same_type: bool = True,
) -> Callable[[S, object], S]:
    """Build an operator method whose result is ``type(self)(func(a, b))``, so it is re-validated.

    The other operand may be the same concrete type (when ``same_type``) or a raw value whose exact
    type is in ``operands`` (default: the class's ``operand_types``, or none). Anything else returns
    NotImplemented, so mixing VO types is a TypeError. Overflow (OverflowError, or decimal.Overflow
    from a context that traps it) becomes OutOfRangeError.
    """

    def method(self: S, other: object) -> S:
        allowed = getattr(type(self), "operand_types", ()) if operands is None else operands
        if same_type and type(other) is type(self):
            operand = other._value
        elif type(other) in allowed:
            operand = other
        else:
            return NotImplemented  # type: ignore[no-any-return]
        try:
            result = func(operand, self._value) if reflected else func(self._value, operand)
        except _OVERFLOW as exc:
            raise _overflow(exc, type(self), (self, other)) from exc
        return type(self)(result)

    return method


def unary_op(func: Callable[[Any], Any]) -> Callable[[S], S]:
    """Build a unary operator method whose result is ``type(self)(func(value))``, re-validated like binary_op."""

    def method(self: S) -> S:
        try:
            result = func(self._value)
        except _OVERFLOW as exc:  # -timedelta.max
            raise _overflow(exc, type(self), self) from exc
        return type(self)(result)

    return method
