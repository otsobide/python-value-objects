"""Static typing contract: checked by mypy --strict, never executed."""

import operator
import re
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import assert_type

from pyvalueobjects import (
    Bounded,
    DecimalNumber,
    Float,
    Int,
    InvalidTypeError,
    Percentage,
    PositiveDecimal,
    PositiveFloat,
    PositiveInt,
    Scalar,
    Sized,
    ValueObject,
    ValueObjectError,
)
from pyvalueobjects._core import binary_op, literal, unary_op


class Code(Scalar[str]):
    accepts = (str,)


class Age(Bounded[int]):
    accepts = (int,)
    operand_types = (int,)
    ge = 0
    __add__ = binary_op(operator.add)
    __radd__ = binary_op(operator.add, reflected=True)
    __neg__ = unary_op(operator.neg)


class Adult(Age):
    ge = 18


class Name(Sized[str]):
    accepts = (str,)
    max_length = 10


class Pair(ValueObject):
    __slots__ = ("left", "right")
    left: Code
    right: Code

    def __init__(self, left: Code | str, right: Code | str) -> None:
        cls = type(self)
        self._set(left=cls._component("left", Code, left), right=cls._component("right", Code, right))


assert_type(Code("a").value, str)
assert_type(Age(1).value, int)
assert_type(Name("x").value, str)
assert_type(Code.from_str("a"), Code)
assert_type(Adult.from_str("20"), Adult)
assert_type(Age.from_optional(None), Age | None)
assert_type(Pair.from_optional(None, None), Pair | None)
assert_type(Code.is_valid("a"), bool)
assert_type(Code("a").replace(value="b"), Code)
assert_type(Pair("a", "b").replace(left="c"), Pair)
assert_type(Pair("a", "b").left, Code)
assert_type(Code("a") == Code("b"), bool)
assert_type(Code("a") < Code("b"), bool)
assert_type(Adult(20) + 1, Adult)
assert_type(1 + Adult(20), Adult)
assert_type(-Age(1), Age)
assert_type(str(Code("a")), str)
assert_type(InvalidTypeError("bad", vo=Code, value=1).vo, type | None)
assert_type(ValueObjectError("bad").reason, str)
assert_type(literal(re.compile("[0-9]+"), int), Callable[[str], int])
assert_type(literal(re.compile("[0-9-]+"), date.fromisoformat), Callable[[str], date])
match Code("a"):
    case Code(value):
        assert_type(value, str)

Code("a").value = "b"  # type: ignore[misc]  # read-only: an unused ignore would fail mypy

# numbers
assert_type(PositiveInt(1).value, int)
assert_type(PositiveInt.from_str("1"), PositiveInt)
assert_type(PositiveInt.from_optional(None), PositiveInt | None)
assert_type(Int(PositiveInt(1)), Int)
assert_type(int(Int(1)), int)
assert_type(Int(1).is_negative(), bool)
assert_type(PositiveInt(1) + 1, PositiveInt)
assert_type(2 * PositiveInt(1), PositiveInt)
assert_type(PositiveInt(3) - PositiveInt(1), PositiveInt)
assert_type(Int(7) // 2, Int)
assert_type(7 % Int(2), Int)
assert_type(-Int(1), Int)
assert_type(+PositiveInt(1), PositiveInt)
assert_type(abs(Int(-1)), Int)
assert_type(Float(1.5).value, float)
assert_type(Float(1) / 2, Float)
assert_type(2.5 * PositiveFloat(1.0), PositiveFloat)
assert_type(float(Float(1.5)), float)
assert_type(DecimalNumber("1.5").value, Decimal)
assert_type(DecimalNumber(1) / 3, DecimalNumber)
assert_type(Decimal("0.5") * PositiveDecimal(2), PositiveDecimal)
assert_type(-DecimalNumber("1.5"), DecimalNumber)
assert_type(PositiveDecimal("2.675").rounded(2), PositiveDecimal)
assert_type(Percentage("10").ratio, Decimal)
assert_type(Percentage("10").of(Decimal(1)), Decimal)
assert_type(Percentage("10").of(PositiveDecimal(5)), PositiveDecimal)
assert_type(Percentage("10") + 5, Percentage)
match PositiveInt(5):
    case PositiveInt(number):
        assert_type(number, int)

PositiveInt("5")  # type: ignore[arg-type]  # must stay rejected
Float("1.5")  # type: ignore[arg-type]
DecimalNumber(1.5)  # type: ignore[arg-type]
Percentage("10").of(1.5)  # type: ignore[type-var]
