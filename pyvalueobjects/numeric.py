"""Numbers: the Int and Float families, on the shared Numeric base."""

from __future__ import annotations

import math
import operator
import re
import sys
from typing import TYPE_CHECKING, ClassVar, Self

from pyvalueobjects._core import (
    Bounded,
    OutOfRangeError,
    PrecisionError,
    Scalar,
    T,
    binary_op,
    literal,
    show,
    unary_op,
)

__all__ = [
    "Float",
    "Int",
    "NegativeFloat",
    "NegativeInt",
    "NegativeOrZeroFloat",
    "NegativeOrZeroInt",
    "Numeric",
    "PositiveFloat",
    "PositiveInt",
    "PositiveOrZeroFloat",
    "PositiveOrZeroInt",
]

_INT_LITERAL = re.compile(r"[+-]?[0-9]+", re.ASCII)
_DECIMAL_LITERAL = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?", re.ASCII)

# sys.set_int_max_str_digits() refuses limits under 640 digits, and an int of at most 2126 bits has at most 640.
_ALWAYS_PRINTABLE_BITS = 2126


class Numeric(Bounded[T], abstract=True):
    """Arithmetic that keeps the left operand's concrete type and re-validates the result.

    Operands: the same concrete type, or a raw number whose exact type is in ``operand_types``.
    Anything else (a parent, child or sibling VO, ``bool``) is a TypeError: convert explicitly.
    """

    operand_types: ClassVar[tuple[type, ...]] = ()

    __add__, __radd__ = binary_op(operator.add), binary_op(operator.add, reflected=True)
    __sub__, __rsub__ = binary_op(operator.sub), binary_op(operator.sub, reflected=True)
    __mul__, __rmul__ = binary_op(operator.mul), binary_op(operator.mul, reflected=True)
    __neg__, __abs__ = unary_op(operator.neg), unary_op(abs)

    def __pos__(self) -> Self:
        return self

    def is_zero(self) -> bool:
        return not self._value

    def is_positive(self) -> bool:
        return self._value > 0  # type: ignore[operator]

    def is_negative(self) -> bool:
        return self._value < 0  # type: ignore[operator]


# --------------------------------------------------------------------------------------------- integers


class Int(Numeric[int]):
    """Arbitrary-precision integer. ``bool`` is never an int; IntEnum members become plain ints.

    The value must have a text form: at most ``sys.get_int_max_str_digits()`` digits (4300 by default),
    so ``str()``, ``repr()`` and ``from_str()`` work for every Int.
    """

    accepts = (int,)
    operand_types = (int,)
    _parse_str = staticmethod(literal(_INT_LITERAL, int))  # exact for any size, unlike float()

    if TYPE_CHECKING:

        def __init__(self, value: int | Scalar[int]) -> None: ...

    __floordiv__, __rfloordiv__ = binary_op(operator.floordiv), binary_op(operator.floordiv, reflected=True)
    __mod__, __rmod__ = binary_op(operator.mod), binary_op(operator.mod, reflected=True)

    @classmethod
    def _validate(cls, value: int) -> int:
        bits = value.bit_length()
        if bits > _ALWAYS_PRINTABLE_BITS and (limit := sys.get_int_max_str_digits()) and abs(value) >= 10**limit:
            reason = f"must have at most {limit} digits (sys.get_int_max_str_digits()), got {show(value)}"
            raise OutOfRangeError(reason, vo=cls, value=value)
        return super()._validate(value)

    def __int__(self) -> int:
        return self._value

    __index__ = __int__  # usable in range(), slicing, hex()


class PositiveOrZeroInt(Int):
    ge = 0


class PositiveInt(PositiveOrZeroInt):
    gt = 0


class NegativeOrZeroInt(Int):
    le = 0


class NegativeInt(NegativeOrZeroInt):
    lt = 0


# --------------------------------------------------------------------------------------------- floats


class Float(Numeric[float]):
    """Finite binary float; ``-0.0`` becomes ``0.0``. An int is converted only when a float holds it exactly."""

    accepts = (float, int)
    operand_types = (float, int)
    _parse_str = staticmethod(literal(_DECIMAL_LITERAL, float))

    if TYPE_CHECKING:

        def __init__(self, value: float | Scalar[float]) -> None: ...

    __truediv__, __rtruediv__ = binary_op(operator.truediv), binary_op(operator.truediv, reflected=True)

    @classmethod
    def _convert(cls, raw: float) -> float:
        try:
            value = float(raw) + 0.0  # int -> float; -0.0 -> 0.0
        except OverflowError:
            raise OutOfRangeError(f"too large for a float, got {show(raw)}", vo=cls, value=raw) from None
        if isinstance(raw, int) and value != raw:  # float() rounds an int beyond 2**53 silently
            raise PrecisionError(f"not exactly representable as a float, got {show(raw)}", vo=cls, value=raw)
        return value

    @classmethod
    def _validate(cls, value: float) -> float:
        if not math.isfinite(value):
            raise OutOfRangeError(f"must be finite, got {value}", vo=cls, value=value)
        return super()._validate(value)

    def __float__(self) -> float:
        return self._value


class PositiveOrZeroFloat(Float):
    ge = 0.0


class PositiveFloat(PositiveOrZeroFloat):
    gt = 0.0


class NegativeOrZeroFloat(Float):
    le = 0.0


class NegativeFloat(NegativeOrZeroFloat):
    lt = 0.0
