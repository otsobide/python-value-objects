"""The numbers of pyvalueobjects.numeric, beyond the generic contract that test_contract.py runs on their samples."""

from __future__ import annotations

import decimal
import enum
import math
import operator
import sys
from collections.abc import Callable
from decimal import ROUND_HALF_EVEN, Decimal, DivisionByZero, InvalidOperation, Overflow
from fractions import Fraction
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pyvalueobjects import numeric
from pyvalueobjects._core import Bounded, InvalidFormatError, InvalidTypeError, OutOfRangeError, PrecisionError, show
from pyvalueobjects.numeric import (
    DECIMAL_CONTEXT,
    DecimalNumber,
    Float,
    Int,
    NegativeDecimal,
    NegativeFloat,
    NegativeInt,
    NegativeOrZeroDecimal,
    NegativeOrZeroFloat,
    NegativeOrZeroInt,
    Numeric,
    PositiveDecimal,
    PositiveFloat,
    PositiveInt,
    PositiveOrZeroDecimal,
    PositiveOrZeroFloat,
    PositiveOrZeroInt,
)

# ------------------------------------------------------------------------------------------- shared tables

# Each family root, with the suffix of its sign variants and the raw value it stores for an int.
FAMILIES: dict[type[Numeric[Any]], tuple[str, Callable[[int], Any]]] = {
    Int: ("Int", int),
    Float: ("Float", float),
    DecimalNumber: ("Decimal", Decimal),
}
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


def compute(expression: str) -> Any:
    """Evaluates one of the expressions below (our own literals) with this module's names."""
    return eval(expression, globals())


def operand_name(obj: object) -> str:
    """The type name an operator TypeError shows: C types outside builtins carry their module."""
    return {Decimal: "decimal.Decimal"}.get(type(obj), type(obj).__name__)


class Signal(enum.IntEnum):
    DOWN = -1
    UP = 1


class Digits(enum.StrEnum):
    SEVEN = "7"


class Thrifty(Decimal):
    """A Decimal subclass: not a Decimal for the type gate, which only converts int, float and str subclasses."""


# User subclasses: the declarative knobs (bounds) and the cooperative _validate chain.


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


# ------------------------------------------------------------------------------------------- Int: text

INT_TEXTS = [
    ("0", 0), ("-0", 0), ("+7", 7), ("007", 7), ("-42", -42), (" 42 ", 42), ("\t-3\n", -3),
    ("9007199254740993", 2**53 + 1), ("-9007199254740993", -(2**53) - 1),
    ("123456789012345678901234567890", 123456789012345678901234567890), (str(2**200), 2**200),
]  # fmt: skip
NOT_INT_TEXTS = [
    "", " ", "+", "-", "--1", "+-1", "1-", "39.0", "39.5", "-39.1", "1.", ".5", "1e3", "1E3", "1e-400", "0x10", "0b1",
    "0o7", "1_000", "1 000", "1,000", "١٢", "５", "𝟕", "²", "½", "\xa07", "7\u2003", "7\u2028", "nan", "inf", "seven",
]  # fmt: skip


@pytest.mark.parametrize(("text", "value"), INT_TEXTS)
def test_from_str_reads_an_integer_literal_exactly(text: str, value: int) -> None:
    number = Int.from_str(text)
    assert number.value == value and type(number.value) is int


@pytest.mark.parametrize("cls", members(Int))
@pytest.mark.parametrize("text", NOT_INT_TEXTS)
def test_from_str_rejects_everything_but_an_ascii_integer(cls: type[Int], text: str) -> None:
    with pytest.raises(InvalidFormatError) as info:
        cls.from_str(text)
    assert str(info.value) == f"{cls.__name__}: cannot parse {show(text)}" and type(info.value.__cause__) is ValueError


@pytest.mark.parametrize(
    ("cls", "text", "message"),
    [
        (PositiveInt, "0", "PositiveInt: value must be > 0, got 0"),
        (PositiveInt, "-5", "PositiveInt: value must be > 0, got -5"),
        (PositiveOrZeroInt, "-1", "PositiveOrZeroInt: value must be >= 0, got -1"),
        (NegativeInt, "5", "NegativeInt: value must be < 0, got 5"),
        (NegativeOrZeroInt, " +1 ", "NegativeOrZeroInt: value must be <= 0, got 1"),
    ],
)
def test_from_str_applies_the_bounds_of_the_class(cls: type[Int], text: str, message: str) -> None:
    with pytest.raises(OutOfRangeError, match=f"^{message}$"):
        cls.from_str(text)


@pytest.mark.parametrize("raw", [0, 39.0, True, b"39", Decimal("39"), Signal.UP, None, ["1"]])
def test_from_str_takes_only_text(raw: Any) -> None:
    with pytest.raises(InvalidTypeError, match=f"^PositiveInt: from_str expects str, got {type(raw).__name__}$"):
        PositiveInt.from_str(raw)


def test_from_str_reads_a_str_enum_member_as_its_text() -> None:
    assert PositiveInt.from_str(Digits.SEVEN) == PositiveInt(7)


@given(
    st.integers(-(10**60), 10**60), st.sampled_from(["", " ", "\t\n"]), st.booleans(), st.sampled_from(["", "0", "00"])
)
def test_from_str_round_trips_through_any_spelling(number: int, pad: str, plus: bool, zeros: str) -> None:
    sign = "-" if number < 0 else "+" if plus else ""
    assert Int.from_str(f"{pad}{sign}{zeros}{abs(number)}{pad}") == Int(number) == Int.from_str(str(Int(number)))


# ------------------------------------------------------------------------------------------- Int: regressions (#34)


def test_regression_C09_from_str_keeps_every_digit_of_a_big_integer() -> None:
    """C09 (#34): 0.x parsed through float(), so '9007199254740993' became 9007199254740992."""
    for text in ("9007199254740993", "-9007199254740993", "123456789012345678901234567890"):
        assert Int.from_str(text).value == int(text)


@pytest.mark.parametrize(
    "text", ["0.99999999999999999", "1.0000000000000001", "39.00000000000000001", "1e-400", "-1e-400"]
)
def test_regression_C10_from_str_rejects_text_that_only_rounds_to_an_integer(text: str) -> None:
    """C10 (#34): 0.x checked is_integer() on the parsed float, so these became 1, 1, 39, 0 and 0."""
    with pytest.raises(InvalidFormatError, match=r"^Int: cannot parse "):
        Int.from_str(text)


def test_regression_C11_from_str_reads_integers_beyond_the_float_range() -> None:
    """C11 (#34): float('1' * 400) is inf, so 0.x refused text that the constructor accepted as an int."""
    assert Int.from_str("1" * 400) == Int(int("1" * 400))


@pytest.mark.parametrize("raw", [True, False, b"39", 39, 39.0, Decimal("39"), Signal.UP])
def test_regression_C12_from_str_rejects_what_is_not_text(raw: Any) -> None:
    """C12 (#34): 0.x had no type check, so from_str(True) built Int(1) and bytes, floats and Decimals passed."""
    with pytest.raises(InvalidTypeError, match=r"^Int: from_str expects str, got "):
        Int.from_str(raw)


@pytest.mark.parametrize(
    ("parse", "error", "message"),
    [
        (lambda: PositiveInt.from_str("-5"), OutOfRangeError, "PositiveInt: value must be > 0, got -5"),
        (lambda: NegativeInt.from_str("5"), OutOfRangeError, "NegativeInt: value must be < 0, got 5"),
        (lambda: Int.from_str("39.5"), InvalidFormatError, "Int: cannot parse '39.5'"),
    ],
)
def test_regression_C13_from_str_keeps_the_real_cause(parse: Callable[[], Int], error: type, message: str) -> None:
    """C13 (#34): 0.x replaced every failure, bounds included, with 'Input type should be number format strings.'."""
    with pytest.raises(error) as info:
        parse()
    assert type(info.value) is error and str(info.value) == message


@pytest.mark.parametrize("cls", members(Int))
@pytest.mark.parametrize("text", ["39.1", "-39.1", "0.5", "-0.5"])
def test_regression_C14_C46_from_str_rejects_decimals_for_every_int_class(cls: type[Int], text: str) -> None:
    """C14/C46 (#34): the 0.x '*from_str*_with_decimals' tests called from_float, so a truncating from_str passed.

    A truncated value would be accepted by some class or fail on its bounds: only a parse error passes here.
    """
    with pytest.raises(InvalidFormatError) as info:
        cls.from_str(text)
    assert type(info.value) is InvalidFormatError


def test_regression_C54_from_str_rejects_zero_text_for_positive_int_on_its_bound() -> None:
    """C54 (#34): the 0.x zero test passed the int 0, so it never parsed '0'; the bound must be what rejects it."""
    with pytest.raises(OutOfRangeError, match=r"^PositiveInt: value must be > 0, got 0$"):
        PositiveInt.from_str("0")
    with pytest.raises(InvalidTypeError):
        PositiveInt.from_str(0)


@pytest.mark.parametrize("text", ["1_000", "١٢", "５", "1e3", "\xa012", "12\u3000"])
def test_regression_X02_from_str_reads_only_ascii_digits(text: str) -> None:
    """X02 (#34): 0.x went through float(), which reads PEP 515 underscores, any Unicode digit and exponents.

    Surrounding ASCII whitespace is stripped, as for every text format; any other whitespace is rejected.
    """
    with pytest.raises(InvalidFormatError):
        Int.from_str(text)
    assert Int.from_str(" 12\n") == Int(12)


# ------------------------------------------------------------------------------------------- Int: the digit limit

LIMIT = 10**4300  # the smallest int with more digits than the default limit of 4300


@pytest.mark.usefixtures("int_digit_limit")
@pytest.mark.parametrize(
    ("cls", "raw", "shown"),
    [
        (Int, LIMIT, "<int with 14285 bits>"),
        (Int, -LIMIT, "<negative int with 14285 bits>"),
        (PositiveInt, LIMIT * 7, "<int with 14288 bits>"),
        (NegativeInt, -LIMIT, "<negative int with 14285 bits>"),
    ],
    ids=["Int", "Int-negative", "PositiveInt", "NegativeInt"],
)
def test_regression_X04_an_int_without_a_text_form_is_out_of_range(cls: type[Int], raw: int, shown: str) -> None:
    """X04 (#34): 0.x accepted Int(10**5000), whose str_value() then raised a plain ValueError."""
    with pytest.raises(OutOfRangeError) as info:
        cls(raw)
    assert (
        str(info.value) == f"{cls.__name__}: must have at most 4300 digits (sys.get_int_max_str_digits()), got {shown}"
    )
    assert info.value.value == raw and not cls.is_valid(raw)


@pytest.mark.usefixtures("int_digit_limit")
@pytest.mark.parametrize("raw", [LIMIT - 1, 1 - LIMIT], ids=["positive", "negative"])
def test_the_longest_int_round_trips_through_text(raw: int) -> None:
    number = Int(raw)
    assert len(str(number).lstrip("-")) == 4300 and eval(repr(number)) == number and Int.from_str(str(number)) == number
    assert format(number, ",").count(",") == 1433


@pytest.mark.usefixtures("int_digit_limit")
def test_from_str_refuses_text_over_the_digit_limit() -> None:
    with pytest.raises(InvalidFormatError, match=r"^Int: cannot parse '1111"):
        Int.from_str("1" * 4301)
    with pytest.raises(InvalidFormatError, match=r"^Int: cannot parse '0000"):
        Int.from_str("0" * 4300 + "1")  # int() counts leading zeros


@pytest.mark.usefixtures("int_digit_limit")
@pytest.mark.parametrize("expression", ["Int(10**4299) * 10", "10 * Int(-(10**4299))", "Int(LIMIT - 1) + 1"])
def test_an_operation_cannot_leave_the_digit_limit(expression: str) -> None:
    with pytest.raises(OutOfRangeError, match=r"^Int: must have at most 4300 digits "):
        compute(expression)


@pytest.mark.parametrize(
    ("limit", "accepted", "rejected"), [(640, 10**640 - 1, 10**640), (5000, LIMIT, 10**5000)], ids=["640", "5000"]
)
def test_the_digit_limit_follows_the_interpreter_setting(
    int_digit_limit: int, limit: int, accepted: int, rejected: int
) -> None:
    sys.set_int_max_str_digits(limit)  # the fixture restores the setting
    assert Int(accepted).value == accepted and str(Int(accepted)) == str(accepted)
    with pytest.raises(OutOfRangeError, match=f"^Int: must have at most {limit} digits "):
        Int(rejected)


def test_without_a_digit_limit_every_int_is_accepted(int_digit_limit: int) -> None:
    sys.set_int_max_str_digits(0)
    assert Int.from_str(str(Int(10**5000))) == Int(10**5000)


# ------------------------------------------------------------------------------------------- Float: values and types

NOT_FLOATS = [
    ("1.5", "str"),
    (True, "bool"),
    (Decimal("1.5"), "Decimal"),
    (None, "NoneType"),
    (Fraction(1, 2), "Fraction"),
]
NOT_FLOATS += [(1j, "complex"), (b"1", "bytes"), ([1.0], "list"), (Digits.SEVEN, "Digits")]


class Heavy(float):
    def __float__(self) -> float:
        return 99.0


@pytest.mark.parametrize("cls", members(Float))
@pytest.mark.parametrize(("raw", "kind"), NOT_FLOATS)
def test_float_accepts_only_float_and_int(cls: type[Float], raw: Any, kind: str) -> None:
    with pytest.raises(InvalidTypeError, match=f"^{cls.__name__}: expected float or int, got {kind}$"):
        cls(raw)


@pytest.mark.parametrize(
    ("raw", "value"),
    [
        (3, 3.0),
        (-7, -7.0),
        (2**53, 2.0**53),
        (-(2**53), -(2.0**53)),
        (10**22, 1e22),
        (Signal.UP, 1.0),
        (Heavy(2.5), 2.5),
    ],
)
def test_float_converts_ints_and_float_subclasses_to_a_plain_float(raw: Any, value: float) -> None:
    number = Float(raw)
    assert number.value == value and type(number.value) is float


@pytest.mark.parametrize("cls", [Float, PositiveOrZeroFloat, NegativeOrZeroFloat])
@pytest.mark.parametrize("raw", [-0.0, 0.0, 0])
def test_negative_zero_becomes_zero(cls: type[Float], raw: float) -> None:
    number = cls(raw)
    assert math.copysign(1.0, number.value) == 1.0 and str(number) == "0.0" and number == cls(0.0)


@pytest.mark.parametrize("cls", members(Float))
@pytest.mark.parametrize("raw", [math.nan, math.inf, -math.inf])
def test_float_must_be_finite_whatever_its_bounds(cls: type[Float], raw: float) -> None:
    with pytest.raises(OutOfRangeError) as info:
        cls(raw)
    assert str(info.value) == f"{cls.__name__}: must be finite, got {raw}" and info.value.vo is cls


@pytest.mark.parametrize(("raw", "shown"), [(10**400, show(10**400)), (-(10**400), show(-(10**400)))])
def test_an_int_beyond_the_float_range_is_out_of_range(raw: int, shown: str) -> None:
    with pytest.raises(OutOfRangeError) as info:
        Float(raw)
    assert str(info.value) == f"Float: too large for a float, got {shown}" and len(shown) == 80


@pytest.mark.parametrize("cls", [Float, PositiveFloat])
@pytest.mark.parametrize("raw", [2**53 + 1, 2**60 + 1, 10**23, 3**40])
def test_regression_X03_an_int_that_no_float_holds_exactly_is_refused(cls: type[Float], raw: int) -> None:
    """X03 (#34): 0.x Float.from_int(2**53 + 1) silently stored 9007199254740992.0. Convert explicitly to round."""
    with pytest.raises(PrecisionError) as info:
        cls(raw)
    assert str(info.value) == f"{cls.__name__}: not exactly representable as a float, got {raw}"
    assert cls(float(raw)).value == float(raw)


@given(st.integers(-(2**1100), 2**1100))
def test_an_int_converts_exactly_or_not_at_all(number: int) -> None:
    try:
        assert Float(number).value == number
    except PrecisionError:
        assert float(number) != number
    except OutOfRangeError:
        assert abs(number) > sys.float_info.max


@pytest.mark.parametrize(
    ("cls", "raw", "expected"),
    [
        (Float, Int(3), Float(3.0)),
        (Float, PositiveFloat(2.5), Float(2.5)),
        (PositiveFloat, Float(2.5), PositiveFloat(2.5)),
    ],
)
def test_another_number_converts_explicitly(cls: type[Numeric[Any]], raw: Numeric[Any], expected: Numeric[Any]) -> None:
    assert cls(raw) == expected and type(cls(raw)) is cls


def test_a_float_never_converts_to_an_int_implicitly() -> None:
    with pytest.raises(InvalidTypeError, match=r"^Int: expected int, got float$"):
        Int(Float(1.0))
    for convert in (int, operator.index):
        with pytest.raises(TypeError):
            convert(Float(1.0))
    assert float(Float(1.5)) == 1.5 and type(float(PositiveFloat(1.5))) is float


@pytest.mark.parametrize(
    ("number", "spec", "text"),
    [
        (Float(1234.5), "", "1234.5"),
        (Float(1234.5), ",.2f", "1,234.50"),
        (Float(0.25), ".0%", "25%"),
        (Float(3), "", "3.0"),
    ],
)
def test_float_formats_like_its_value(number: Float, spec: str, text: str) -> None:
    assert format(number, spec) == text


# ------------------------------------------------------------------------------------------- Float: text

FLOAT_TEXTS = [
    ("1.5", 1.5), ("-0.0", 0.0), ("+1", 1.0), ("1.", 1.0), (".5", 0.5), ("1e3", 1000.0), ("1E-3", 0.001),
    (" 2.5 ", 2.5), ("\t007.50\n", 7.5), ("1e-400", 0.0), ("9007199254740993", 2.0**53),
    ("1.7976931348623157e308", 1.7976931348623157e308), ("5e-324", 5e-324),
]  # fmt: skip
NOT_FLOAT_TEXTS = [
    "", " ", ".", "-.", "e3", "1e", "1e3.5", "1 e3", "1.5.2", "1,5", "+-1", "--1", "0x1p3", "nan", "NaN", "inf", "-inf",
    "Infinity", "1_0", "1_000.5", "١", "٣.٥", "５", "\xa01", "1\u2003", "1.5f",
]  # fmt: skip


@pytest.mark.parametrize(("text", "value"), FLOAT_TEXTS)
def test_float_from_str_reads_a_decimal_literal(text: str, value: float) -> None:
    number = Float.from_str(text)
    assert number.value == value and math.copysign(1.0, number.value) == math.copysign(1.0, value)


@pytest.mark.parametrize("cls", members(Float))
@pytest.mark.parametrize("text", NOT_FLOAT_TEXTS)
def test_float_from_str_rejects_everything_but_an_ascii_decimal_literal(cls: type[Float], text: str) -> None:
    with pytest.raises(InvalidFormatError) as info:
        cls.from_str(text)
    assert str(info.value) == f"{cls.__name__}: cannot parse {show(text)}" and type(info.value.__cause__) is ValueError


@pytest.mark.parametrize(
    ("cls", "text", "message"),
    [
        (Float, "1e400", "Float: must be finite, got inf"),
        (Float, "-1e400", "Float: must be finite, got -inf"),
        (PositiveFloat, "0", "PositiveFloat: value must be > 0.0, got 0.0"),
        (PositiveFloat, "-0.0", "PositiveFloat: value must be > 0.0, got 0.0"),
        (NegativeFloat, "1e-400", "NegativeFloat: value must be < 0.0, got 0.0"),
        (PositiveOrZeroFloat, "-0.1", "PositiveOrZeroFloat: value must be >= 0.0, got -0.1"),
    ],
)
def test_float_from_str_applies_the_rules_of_the_class(cls: type[Float], text: str, message: str) -> None:
    with pytest.raises(OutOfRangeError, match=f"^{message}$"):
        cls.from_str(text)


@pytest.mark.parametrize("text", ["1_000", "١٢", "５", "\xa012"])
def test_regression_X02_float_from_str_reads_only_ascii_digits(text: str) -> None:
    """X02 (#34): 0.x Float.from_str went through float(), which reads PEP 515 underscores and any Unicode digit."""
    with pytest.raises(InvalidFormatError):
        Float.from_str(text)
    assert Float.from_str("1e3") == Float(1000.0)  # an exponent is part of a float literal


@given(st.floats(allow_nan=False, allow_infinity=False))
def test_float_text_round_trips(number: float) -> None:
    assert Float.from_str(repr(number)) == Float(number) == Float.from_str(str(Float(number)))


# ------------------------------------------------------------------------------------------- DecimalNumber: values and types

NOT_DECIMALS = [(1.5, "float"), (True, "bool"), (None, "NoneType"), (b"1", "bytes"), ([1], "list"), (1j, "complex")]
NOT_DECIMALS += [(Fraction(1, 2), "Fraction"), (Float(1.5), "float"), (Thrifty("1.5"), "Thrifty")]


def test_decimal_context_is_decimal128_and_traps_what_would_lose_meaning() -> None:
    assert (DECIMAL_CONTEXT.prec, DECIMAL_CONTEXT.rounding) == (34, ROUND_HALF_EVEN)
    assert (DECIMAL_CONTEXT.Emax, DECIMAL_CONTEXT.Emin) == (999999, -999999)
    assert {signal for signal, on in DECIMAL_CONTEXT.traps.items() if on} == {
        InvalidOperation,
        DivisionByZero,
        Overflow,
    }


@pytest.mark.parametrize("cls", members(DecimalNumber))
@pytest.mark.parametrize(("raw", "kind"), NOT_DECIMALS)
def test_decimal_never_accepts_a_float(cls: type[DecimalNumber], raw: Any, kind: str) -> None:
    with pytest.raises(InvalidTypeError, match=f"^{cls.__name__}: expected Decimal or int or str, got {kind}$"):
        cls(raw)


@pytest.mark.parametrize(
    ("raw", "text"),
    [
        (Decimal("1.50"), "1.50"), (7, "7"), (-(2**100), str(-(2**100))), ("1.50", "1.50"), (" 4.10 ", "4.10"),
        ("+1", "1"), ("1.", "1"), (".5", "0.5"), ("1e3", "1E+3"), ("1E-3", "0.001"), ("-0.00", "0.00"),
        (Decimal("-0"), "0"), (Decimal("-0E+3"), "0E+3"), (Signal.UP, "1"), (Digits.SEVEN, "7"), (Int(5), "5"),
        ("123.456789012345678901234567890", "123.456789012345678901234567890"), (10**40, "1" + "0" * 40),
    ],
)  # fmt: skip
def test_decimal_keeps_the_exact_value_and_scale(raw: Any, text: str) -> None:
    number = DecimalNumber(raw)
    assert str(number) == text and type(number.value) is Decimal and number.value == Decimal(text)
    assert not number.value.is_signed() or number.value != 0  # never '-0'


def test_decimals_with_another_scale_are_equal() -> None:
    assert DecimalNumber("1.10") == DecimalNumber("1.1") == DecimalNumber(Decimal("1.100"))
    assert hash(DecimalNumber("1.10")) == hash(DecimalNumber("1.1")) and str(DecimalNumber("1.10")) == "1.10"


NOT_DECIMAL_TEXTS = [
    "", " ", ".", "-.", "e3", "1e", "1e3.5", "1.5.2", "1,5", "1 000", "+-1", "0x10", "1_000", "١٢", "５", "\xa01",
    "NaN", "nan", "sNaN", "Infinity", "-Infinity", "inf", "1e99999999999999999999",
]  # fmt: skip


@pytest.mark.parametrize("cls", members(DecimalNumber))
@pytest.mark.parametrize("text", NOT_DECIMAL_TEXTS)
def test_decimal_text_must_be_an_ascii_decimal_literal(cls: type[DecimalNumber], text: str) -> None:
    for build in (cls, cls.from_str):
        with pytest.raises(InvalidFormatError) as info:
            build(text)
        assert str(info.value) == f"{cls.__name__}: cannot parse {show(text)}"


@pytest.mark.parametrize("context", [decimal.Context(), decimal.Context(traps=[])], ids=["trapping", "quiet"])
def test_decimal_parsing_ignores_the_caller_context(context: decimal.Context) -> None:
    """Decimal(text) in a quiet context gives NaN for an exponent beyond any range, and a trapping one raises."""
    with decimal.localcontext(context):
        with pytest.raises(InvalidFormatError, match=r"^DecimalNumber: cannot parse '1e99999999999999999999'$"):
            DecimalNumber("1e99999999999999999999")
        assert DecimalNumber("3.14159265358979323846").value == Decimal("3.14159265358979323846")


@pytest.mark.parametrize("cls", members(DecimalNumber))
@pytest.mark.parametrize("raw", [Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"), Decimal("-Infinity")])
def test_decimal_must_be_finite_whatever_its_bounds(cls: type[DecimalNumber], raw: Decimal) -> None:
    with pytest.raises(OutOfRangeError, match=f"^{cls.__name__}: must be finite, got {raw}$"):
        cls(raw)


@pytest.mark.parametrize(
    ("cls", "raw", "expected"),
    [
        (DecimalNumber, PositiveDecimal("1.5"), DecimalNumber("1.5")),
        (PositiveDecimal, DecimalNumber(2), PositiveDecimal(2)),
    ],
)
def test_another_decimal_converts_explicitly(
    cls: type[DecimalNumber], raw: DecimalNumber, expected: DecimalNumber
) -> None:
    assert cls(raw) == expected and type(cls(raw)) is cls


@pytest.mark.parametrize(
    ("cls", "text", "message"),
    [
        (PositiveDecimal, "0", "PositiveDecimal: value must be > 0, got Decimal('0')"),
        (PositiveDecimal, "-0.00", "PositiveDecimal: value must be > 0, got Decimal('0.00')"),
        (NegativeDecimal, " 1e-30 ", "NegativeDecimal: value must be < 0, got Decimal('1E-30')"),
        (PositiveOrZeroDecimal, "-0.01", "PositiveOrZeroDecimal: value must be >= 0, got Decimal('-0.01')"),
    ],
)
def test_decimal_from_str_applies_the_bounds_of_the_class(cls: type[DecimalNumber], text: str, message: str) -> None:
    with pytest.raises(OutOfRangeError) as info:
        cls.from_str(text)
    assert str(info.value) == message


@given(st.decimals(allow_nan=False, allow_infinity=False, places=8, min_value=-(10**20), max_value=10**20))
def test_decimal_text_round_trips(number: Decimal) -> None:
    built = DecimalNumber(number)
    assert DecimalNumber.from_str(str(built)) == built and str(DecimalNumber(str(built))) == str(built)


# ------------------------------------------------------------------------------------------- arithmetic


# (expression, expected): the result has the left operand's concrete type, even with a raw number on the left
ARITHMETIC = [
    ("PositiveInt(3) + PositiveInt(2)", PositiveInt(5)),
    ("PositiveInt(3) + 2", PositiveInt(5)),
    ("2 + PositiveInt(3)", PositiveInt(5)),
    ("Int(3) - 10", Int(-7)),
    ("10 - PositiveInt(3)", PositiveInt(7)),
    ("Int(-4) * Int(3)", Int(-12)),
    ("3 * NegativeInt(-2)", NegativeInt(-6)),
    ("Int(2**100) * Int(2**100)", Int(2**200)),
    ("Int(7) // 2", Int(3)),
    ("Int(-7) // 2", Int(-4)),
    ("7 // Int(2)", Int(3)),
    ("PositiveInt(7) // PositiveInt(2)", PositiveInt(3)),
    ("Int(7) % 2", Int(1)),
    ("Int(-7) % 3", Int(2)),
    ("7 % Int(-4)", Int(-1)),
    ("-Int(3)", Int(-3)),
    ("-NegativeOrZeroInt(0)", NegativeOrZeroInt(0)),
    ("abs(Int(-3))", Int(3)),
    ("abs(PositiveOrZeroInt(0))", PositiveOrZeroInt(0)),
    ("+NegativeInt(-3)", NegativeInt(-3)),
    ("Age(30) + 1", Age(31)),
    ("1 + Age(30)", Age(31)),
    ("Float(1) / 4", Float(0.25)),
    ("1 / Float(4)", Float(0.25)),
    ("Float(1.5) + Float(2.5)", Float(4.0)),
    ("Float(1.5) + 1", Float(2.5)),
    ("3 - Float(0.5)", Float(2.5)),
    ("2 * Float(1.5)", Float(3.0)),
    ("Float(0.1) + 0.2", Float(0.30000000000000004)),
    ("PositiveFloat(2.0) / PositiveFloat(4.0)", PositiveFloat(0.5)),
    ("-Float(0.0)", Float(0.0)),
    ("NegativeOrZeroFloat(-1.0) * 0", NegativeOrZeroFloat(0.0)),
    ("abs(Float(-2.5))", Float(2.5)),
    ("DecimalNumber('0.1') + Decimal('0.2')", DecimalNumber("0.3")),
    ("Decimal('0.2') + DecimalNumber('0.1')", DecimalNumber("0.3")),
    ("DecimalNumber('0.1') + DecimalNumber('0.2')", DecimalNumber("0.3")),
    ("1 + DecimalNumber('0.5')", DecimalNumber("1.5")),
    ("3 - DecimalNumber('1')", DecimalNumber(2)),
    ("PositiveDecimal('0.5') * PositiveDecimal('0.5')", PositiveDecimal("0.25")),
    ("1 / DecimalNumber(4)", DecimalNumber("0.25")),
    ("-NegativeOrZeroDecimal(0)", NegativeOrZeroDecimal(0)),
    ("abs(DecimalNumber('-2.5'))", DecimalNumber("2.5")),
]
# (expression, str() of the result): exact digits and scale, computed in DECIMAL_CONTEXT under the hostile context
DECIMAL_RESULTS = [
    ("DecimalNumber('1.50') + Decimal('0.20')", "1.70"),
    ("DecimalNumber('1.5') * 2", "3.0"),
    ("DecimalNumber('123.456') * Decimal('1000')", "123456.000"),
    ("DecimalNumber(1) / 3", "0.3333333333333333333333333333333333"),
    ("DecimalNumber(2) / 3", "0.6666666666666666666666666666666667"),
    ("DecimalNumber('9999999999999999999999999999999999') + 1", "1.000000000000000000000000000000000E+34"),
    ("DecimalNumber('1') - Decimal('1.00')", "0.00"),
    ("-DecimalNumber('1.50')", "-1.50"),
    ("-DecimalNumber('0.00')", "0.00"),
    ("abs(DecimalNumber('-0.010'))", "0.010"),
    ("DecimalNumber('1E+999999') - DecimalNumber('1E+999999')", "0E+999999"),
]
# (expression, message): every result goes through the constructor of the left operand's type again
REVALIDATED = [
    ("PositiveInt(1) - PositiveInt(5)", "PositiveInt: value must be > 0, got -4"),
    ("PositiveInt(1) - 1", "PositiveInt: value must be > 0, got 0"),
    ("0 - PositiveOrZeroInt(1)", "PositiveOrZeroInt: value must be >= 0, got -1"),
    ("-PositiveInt(1)", "PositiveInt: value must be > 0, got -1"),
    ("abs(NegativeInt(-3))", "NegativeInt: value must be < 0, got 3"),
    ("NegativeInt(-2) * -1", "NegativeInt: value must be < 0, got 2"),
    ("PositiveInt(1) // 2", "PositiveInt: value must be > 0, got 0"),
    ("PositiveInt(7) % 7", "PositiveInt: value must be > 0, got 0"),
    ("Age(150) + 1", "Age: value must be <= 150, got 151"),
    ("Float(1e308) * 10", "Float: must be finite, got inf"),
    ("Float(-1e308) - 1e308", "Float: must be finite, got -inf"),
    ("Float(1.0) * 10**400", "Float: result out of range: int too large to convert to float"),
    ("PositiveFloat(1.0) - 2", "PositiveFloat: value must be > 0.0, got -1.0"),
    ("PositiveFloat(5e-324) / 2", "PositiveFloat: value must be > 0.0, got 0.0"),
    ("NegativeFloat(-1.0) * 0", "NegativeFloat: value must be < 0.0, got 0.0"),
    ("-PositiveFloat(0.5)", "PositiveFloat: value must be > 0.0, got -0.5"),
    ("PositiveDecimal('1') - 2", "PositiveDecimal: value must be > 0, got Decimal('-1')"),
    ("-PositiveDecimal('0.5')", "PositiveDecimal: value must be > 0, got Decimal('-0.5')"),
    ("NegativeDecimal('-1') * 0", "NegativeDecimal: value must be < 0, got Decimal('0')"),
    ("DecimalNumber('9E+999999') * 10", "DecimalNumber: result out of range: decimal overflow"),
    ("10 * DecimalNumber('-9E+999999')", "DecimalNumber: result out of range: decimal overflow"),
]
# (left, symbol, right): a VO of another type, bool, or a raw type outside operand_types is never an operand
NOT_OPERANDS = [
    (Int(7), "/", 2),
    (Int(7), "/", Int(2)),
    (Int(1), "+", PositiveInt(2)),
    (PositiveInt(1), "+", Int(2)),
    (Int(1), "-", Age(2)),
    (Int(1), "+", 1.5),
    (1.5, "*", Int(1)),
    (Int(1), "+", True),
    (True, "+", Int(1)),
    (Int(1), "%", Decimal(1)),
    (Int(1), "//", Fraction(1)),
    (Int(1), "+", "1"),
    (Int(1), "-", None),
    (Float(1), "+", Decimal(1)),
    (Decimal(1), "*", Float(1)),
    (Float(1), "+", Int(1)),
    (Int(1), "+", Float(1)),
    (Float(1), "-", PositiveFloat(1.0)),
    (Float(1), "*", Fraction(1, 2)),
    (Float(1), "+", True),
    (Float(1), "/", "2"),
    (Float(7), "//", 2),
    (Float(7), "%", 2),
    (DecimalNumber(1), "+", 0.1),
    (0.1, "+", DecimalNumber(1)),
    (DecimalNumber(1), "*", Float(1)),
    (DecimalNumber(1), "+", Int(1)),
    (DecimalNumber(1), "-", PositiveDecimal(1)),
    (DecimalNumber(1), "+", True),
    (DecimalNumber(1), "*", Fraction(1, 2)),
    (DecimalNumber(1), "/", "2"),
    (DecimalNumber(7), "//", 2),
    (DecimalNumber(7), "%", 2),
]


@pytest.mark.parametrize(("expression", "expected"), ARITHMETIC, ids=[row[0] for row in ARITHMETIC])
def test_operators_build_the_left_operand_type(expression: str, expected: Numeric[Any]) -> None:
    result = compute(expression)
    assert result == expected and type(result) is type(expected) and type(result.value) is type(expected.value)


@pytest.mark.parametrize(("expression", "text"), DECIMAL_RESULTS, ids=[row[0] for row in DECIMAL_RESULTS])
def test_decimal_arithmetic_runs_in_the_decimal_context(expression: str, text: str) -> None:
    """The autouse hostile context (3 digits, ROUND_FLOOR) gives other digits to anything computed in it."""
    assert str(compute(expression)) == text


@pytest.mark.parametrize(("expression", "message"), REVALIDATED, ids=[row[0] for row in REVALIDATED])
def test_results_are_validated_again(expression: str, message: str) -> None:
    with pytest.raises(OutOfRangeError) as info:
        compute(expression)
    assert str(info.value) == message


@pytest.mark.parametrize(("left", "symbol", "right"), NOT_OPERANDS, ids=repr)
def test_other_operands_are_a_type_error(left: object, symbol: str, right: object) -> None:
    message = f"unsupported operand type(s) for {symbol}: '{operand_name(left)}' and '{operand_name(right)}'"
    with pytest.raises(TypeError) as info:
        eval(f"left {symbol} right", {"left": left, "right": right})
    assert str(info.value) == message


DIVISIONS_BY_ZERO = ["Int(1) // 0", "Int(1) % 0", "Int(1) // Int(0)", "1 // Int(0)", "1 % Int(0)"]
DIVISIONS_BY_ZERO += ["Float(1) / 0", "1 / Float(0.0)", "Float(1) / Float(0.0)", "Float(0.0) / 0.0"]
DIVISIONS_BY_ZERO += ["DecimalNumber(1) / 0", "DecimalNumber(1) / DecimalNumber(0)", "1 / DecimalNumber(0)"]
DIVISIONS_BY_ZERO += ["DecimalNumber(0) / 0", "DecimalNumber('0.00') / Decimal('-0')", "Decimal(0) / DecimalNumber(0)"]


@pytest.mark.parametrize("expression", DIVISIONS_BY_ZERO)
def test_division_by_zero_propagates(expression: str) -> None:
    """0 / 0 included: DECIMAL_CONTEXT calls it InvalidOperation, which is not a ZeroDivisionError."""
    with pytest.raises(ZeroDivisionError):
        compute(expression)


def test_unary_plus_is_the_number_itself() -> None:
    number = PositiveInt(3)
    assert +number is number


def test_in_place_operators_rebind_and_never_mutate() -> None:
    total = original = PositiveInt(1)
    total += 2
    total *= PositiveInt(3)
    total -= 1
    total //= 2
    total %= 3
    assert total == PositiveInt(1) and original == PositiveInt(1) and type(total) is PositiveInt


# ------------------------------------------------------------------------------------------- extension


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
    assert cls.from_str(f" {raw} ") == number and int(number) == raw and repr(number) == f"{cls.__name__}({raw})"
    assert number != Int(raw) and Int(number) == Int(raw)


@given(st.integers(-200, 200))
def test_is_valid_agrees_with_the_declared_bounds(number: int) -> None:
    assert Age.is_valid(number) is (0 <= number <= 150)
    assert PositiveInt.is_valid(number) is (number > 0) and NegativeOrZeroInt.is_valid(number) is (number <= 0)
