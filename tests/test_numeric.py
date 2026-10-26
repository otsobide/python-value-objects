"""The numbers of pyvalueobjects.numeric, beyond the generic contract that test_contract.py runs on their samples."""

from __future__ import annotations

import enum
import operator
from collections.abc import Callable
from decimal import Decimal
from fractions import Fraction
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pyvalueobjects import numeric
from pyvalueobjects._core import Bounded, InvalidFormatError, InvalidTypeError, OutOfRangeError, show
from pyvalueobjects.numeric import Int, NegativeInt, NegativeOrZeroInt, Numeric, PositiveInt, PositiveOrZeroInt

# ------------------------------------------------------------------------------------------- shared tables

# Each family root, with the suffix of its sign variants and the raw value it stores for an int.
FAMILIES: dict[type[Numeric[Any]], tuple[str, Callable[[int], Any]]] = {Int: ("Int", int)}
# (prefix of the sign variant, its parent's prefix, the bound attribute that rejects, its symbol, accepted signs)
SIGNS = [
    ("PositiveOrZero", None, "ge", ">=", {0, 1}),
    ("Positive", "PositiveOrZero", "gt", ">", {1}),
    ("NegativeOrZero", None, "le", "<=", {0, -1}),
    ("Negative", "NegativeOrZero", "lt", "<", {-1}),
]
VARIANTS = [
    (root, getattr(numeric, prefix + suffix), getattr(numeric, parent + suffix) if parent else root, bound, symbol)
    for root, (suffix, _) in FAMILIES.items()
    for prefix, parent, bound, symbol, _ in SIGNS
]
SIGNED = [
    pytest.param(
        getattr(numeric, prefix + suffix), make, sign, sign in accepted, bound, symbol, id=f"{prefix}{suffix}{sign}"
    )
    for suffix, make in FAMILIES.values()
    for prefix, _, bound, symbol, accepted in SIGNS
    for sign in (-1, 0, 1)
]
CONCRETE = [
    cls for cls in vars(numeric).values() if isinstance(cls, type) and issubclass(cls, Numeric) and not cls._abstract
]


def members(root: type) -> list[Any]:
    """The concrete classes of the family of ``root``, as parameters named after them."""
    return [pytest.param(cls, id=cls.__name__) for cls in CONCRETE if issubclass(cls, root)]


class Signal(enum.IntEnum):
    DOWN = -1
    UP = 1


class Digits(enum.StrEnum):
    SEVEN = "7"


# ------------------------------------------------------------------------------------------- the shared base


def test_numeric_is_an_abstract_bounded_scalar() -> None:
    assert issubclass(Numeric, Bounded) and Numeric._abstract
    with pytest.raises(TypeError, match=r"^Numeric is abstract: subclass it$"):
        Numeric(1)


@pytest.mark.parametrize(
    ("root", "cls", "parent", "bound", "symbol"), VARIANTS, ids=lambda v: getattr(v, "__name__", v)
)
def test_sign_variants_extend_their_family(
    root: type[Numeric[Any]], cls: type[Numeric[Any]], parent: type, bound: str, symbol: str
) -> None:
    assert cls.__bases__ == (parent,) and issubclass(cls, root) and getattr(cls, bound) == 0
    assert vars(cls).keys() & {"gt", "ge", "lt", "le"} == {bound}  # a one-line declaration on the parent


@pytest.mark.parametrize(("cls", "make", "sign", "accepted", "bound", "symbol"), SIGNED)
def test_sign_variants_accept_their_signs_and_name_the_violated_bound(
    cls: type[Numeric[Any]], make: Callable[[int], Any], sign: int, accepted: bool, bound: str, symbol: str
) -> None:
    raw = make(sign)
    if accepted:
        assert cls(raw).value == raw and type(cls(raw).value) is type(raw)
        return
    with pytest.raises(OutOfRangeError) as info:
        cls(raw)
    assert str(info.value) == f"{cls.__name__}: value must be {symbol} {getattr(cls, bound)}, got {show(raw)}"
    assert info.value.vo is cls and info.value.value == raw and not cls.is_valid(raw)


@pytest.mark.parametrize(
    ("raw", "positive", "negative", "zero"),
    [(-2, False, True, False), (0, False, False, True), (3, True, False, False)],
)
def test_sign_predicates(raw: int, positive: bool, negative: bool, zero: bool) -> None:
    for root, (_, make) in FAMILIES.items():
        number = root(make(raw))
        assert (number.is_positive(), number.is_negative(), number.is_zero()) == (positive, negative, zero)


def test_a_zero_is_still_truthy() -> None:
    assert all(bool(root(make(0))) for root, (_, make) in FAMILIES.items())


# ------------------------------------------------------------------------------------------- Int: values and types

NOT_INTS = [("1", "str"), (1.0, "float"), (True, "bool"), (False, "bool"), (Decimal(1), "Decimal"), (None, "NoneType")]
NOT_INTS += [(Fraction(1), "Fraction"), (1j, "complex"), (b"1", "bytes"), ([1], "list"), (Digits.SEVEN, "Digits")]


@pytest.mark.parametrize("cls", members(Int))
@pytest.mark.parametrize(("raw", "kind"), NOT_INTS)
def test_int_accepts_only_int(cls: type[Int], raw: Any, kind: str) -> None:
    with pytest.raises(InvalidTypeError, match=f"^{cls.__name__}: expected int, got {kind}$"):
        cls(raw)


@pytest.mark.parametrize(("cls", "member"), [(Int, Signal.DOWN), (PositiveInt, Signal.UP), (NegativeInt, Signal.DOWN)])
def test_int_enum_members_become_plain_ints(cls: type[Int], member: Signal) -> None:
    number = cls(member)
    assert number == cls(int(member)) and type(number.value) is int and str(number) == str(int(member))


@pytest.mark.parametrize(
    ("cls", "raw", "expected"),
    [
        (Int, PositiveInt(3), Int(3)),
        (PositiveInt, Int(3), PositiveInt(3)),
        (NegativeOrZeroInt, NegativeInt(-2), NegativeOrZeroInt(-2)),
    ],
)
def test_another_int_converts_explicitly(cls: type[Int], raw: Int, expected: Int) -> None:
    assert cls(raw) == expected and type(cls(raw)) is cls


@pytest.mark.parametrize(("cls", "raw"), [(PositiveInt, Int(-3)), (NegativeInt, PositiveOrZeroInt(0))])
def test_a_converted_int_obeys_the_target_bounds(cls: type[Int], raw: Int) -> None:
    with pytest.raises(OutOfRangeError, match=f"^{cls.__name__}: value must be "):
        cls(raw)


def test_int_converts_to_a_python_int_wherever_one_is_needed() -> None:
    three = PositiveInt(3)
    assert int(three) == 3 and type(int(three)) is int and operator.index(three) == 3
    assert list(range(three)) == [0, 1, 2] and "abcd"[Int(1) : three] == "bc" and [10, 20, 30][Int(-1)] == 30
    assert hex(Int(255)) == "0xff" and bin(Int(5)) == "0b101"


@pytest.mark.parametrize(
    ("spec", "text"), [("", "-1234"), ("03d", "-1234"), ("08d", "-0001234"), (",", "-1,234"), ("x", "-4d2")]
)
def test_int_formats_like_its_value(spec: str, text: str) -> None:
    assert format(Int(-1234), spec) == text


def test_ints_equal_and_order_only_within_one_type() -> None:
    assert Int(5) != 5 and Int(5) != PositiveInt(5) and len({Int(5), PositiveInt(5), PositiveOrZeroInt(5)}) == 3
    assert sorted([Int(3), Int(-1), Int(2)]) == [Int(-1), Int(2), Int(3)]
    with pytest.raises(TypeError):
        _ = Int(1) < PositiveInt(2)


@pytest.mark.parametrize(
    ("cls", "raw", "symbol"), [(PositiveInt, -5, ">"), (PositiveInt, 0, ">"), (NegativeInt, 5, "<")]
)
def test_regression_C16_a_strict_variant_names_its_own_bound(cls: type[Int], raw: int, symbol: str) -> None:
    """C16 (#34): PositiveInt(-5) reported its parent's '>= 0', which suggested that 0 was allowed."""
    with pytest.raises(OutOfRangeError, match=f"^{cls.__name__}: value must be {symbol} 0, got {raw}$"):
        cls(raw)


@pytest.mark.parametrize("raw", [float("inf"), float("nan"), 1.0])
def test_regression_C16_a_float_is_a_type_error_for_int_whatever_its_value(raw: float) -> None:
    """C16 (#34): Int.from_float(inf/nan) reported 'float without decimals'; 1.0 has no from_float and floats never pass."""
    with pytest.raises(InvalidTypeError, match=r"^Int: expected int, got float$"):
        Int(raw)


# ------------------------------------------------------------------------------------------- extension


class Age(Int):
    ge = 0
    le = 150


class Quantity(PositiveInt):
    pass


class Even(Int):
    @classmethod
    def _validate(cls, value: int) -> int:
        value = super()._validate(value)
        if value % 2:
            raise InvalidFormatError(f"must be even, got {value}", vo=cls, value=value)
        return value


class EvenPercent(Even, Age):
    le = 100


@pytest.mark.parametrize(
    ("cls", "raw", "error", "message"),
    [
        (Age, -1, OutOfRangeError, "Age: value must be >= 0, got -1"),
        (Age, 151, OutOfRangeError, "Age: value must be <= 150, got 151"),
        (Quantity, 0, OutOfRangeError, "Quantity: value must be > 0, got 0"),
        (Even, 3, InvalidFormatError, "Even: must be even, got 3"),
        (EvenPercent, 102, OutOfRangeError, "EvenPercent: value must be <= 100, got 102"),
        (EvenPercent, 99, InvalidFormatError, "EvenPercent: must be even, got 99"),
        (EvenPercent, "2", InvalidTypeError, "EvenPercent: expected int, got str"),
    ],
)
def test_subclasses_declare_their_own_rules(cls: type[Int], raw: Any, error: type, message: str) -> None:
    with pytest.raises(error) as info:
        cls(raw)
    assert type(info.value) is error and str(info.value) == message and info.value.vo is cls


@pytest.mark.parametrize(("cls", "raw"), [(Age, 0), (Age, 150), (Quantity, 1), (Even, -4), (EvenPercent, 100)])
def test_subclasses_keep_the_int_behaviour(cls: type[Int], raw: int) -> None:
    number = cls(raw)
    assert int(number) == raw and repr(number) == f"{cls.__name__}({raw})"
    assert number != Int(raw) and Int(number) == Int(raw)


@given(st.integers(-200, 200))
def test_is_valid_agrees_with_the_declared_bounds(number: int) -> None:
    assert Age.is_valid(number) is (0 <= number <= 150)
    assert PositiveInt.is_valid(number) is (number > 0) and NegativeOrZeroInt.is_valid(number) is (number <= 0)
