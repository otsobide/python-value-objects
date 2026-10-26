"""Numbers: the Int family, on the shared Numeric base."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from pyvalueobjects._core import Bounded, Scalar, T, literal

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
    """Base of every number: a bounded scalar with sign predicates."""

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
    _parse_str = staticmethod(literal(_INT_LITERAL, int))  # exact for any size, unlike float()

    if TYPE_CHECKING:

        def __init__(self, value: int | Scalar[int]) -> None: ...

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
