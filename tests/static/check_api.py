"""Static typing contract: checked by mypy --strict, never executed."""

import operator
from typing import assert_type

from pyvalueobjects import Bounded, InvalidTypeError, Scalar, Sized, ValueObject, ValueObjectError
from pyvalueobjects._core import binary_op, unary_op


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
match Code("a"):
    case Code(value):
        assert_type(value, str)

Code("a").value = "b"  # type: ignore[misc]  # read-only: an unused ignore would fail mypy
