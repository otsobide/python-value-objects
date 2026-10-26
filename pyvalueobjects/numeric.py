"""Numbers: the Int family, on the shared Numeric base."""

from __future__ import annotations

import operator
import re
from typing import TYPE_CHECKING, ClassVar, Self

from pyvalueobjects._core import Bounded, Scalar, T, binary_op, literal, unary_op

__all__ = [
    "Int",
    "NegativeInt",
    "NegativeOrZeroInt",
    "Numeric",
    "PositiveInt",
    "PositiveOrZeroInt",
]

_INT_LITERAL = re.compile(r"[+-]?[0-9]+", re.ASCII)


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
    """Arbitrary-precision integer. ``bool`` is never an int; IntEnum members become plain ints."""

    accepts = (int,)
    operand_types = (int,)
    _parse_str = staticmethod(literal(_INT_LITERAL, int))  # exact for any size, unlike float()

    if TYPE_CHECKING:

        def __init__(self, value: int | Scalar[int]) -> None: ...

    __floordiv__, __rfloordiv__ = binary_op(operator.floordiv), binary_op(operator.floordiv, reflected=True)
    __mod__, __rmod__ = binary_op(operator.mod), binary_op(operator.mod, reflected=True)

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
