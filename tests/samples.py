"""Registry of inputs per value object, consumed by test_contract.py. One Sample per concrete public VO."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import pyvalueobjects as vo
from pyvalueobjects import numeric


class Args(tuple[Any, ...]):
    """Positional arguments for composite constructors: ``Args("10.00", "EUR")``."""

    def __new__(cls, *args: Any) -> Args:
        return super().__new__(cls, args)


@dataclass(frozen=True)
class Sample:
    cls: type[vo.ValueObject]
    valid: list[Any]  # >= 2 inputs with distinct values; Args(...) for composites
    invalid: list[Any] = field(default_factory=list)  # ValueObjectError, but not InvalidTypeError
    wrong_type: list[Any] = field(default_factory=list)  # InvalidTypeError
    normalized: list[tuple[Any, str]] = field(default_factory=list)  # (raw, expected str())
    str_roundtrip: bool = True  # cls.from_str(str(x)) == x

    def build(self, raw: Any) -> vo.ValueObject:
        return self.cls(*raw) if isinstance(raw, Args) else self.cls(raw)

    @property
    def id(self) -> str:
        return self.cls.__name__


class Level(enum.IntEnum):
    HIGH = 3


NOT_INT = ["1", None, True, 1.0, Decimal(1), [1]]
NOT_FLOAT = ["1.5", None, True, Decimal(1), [1.0]]
NOT_DECIMAL = [1.5, None, True, b"1", [1]]

# Each family adds a Sample per value object in the commit that adds the value object (B3-B9).
SAMPLES: list[Sample] = [
    # numbers
    Sample(numeric.Int, [0, -7, 2**100], wrong_type=NOT_INT, normalized=[(Level.HIGH, "3")]),
    Sample(numeric.PositiveOrZeroInt, [0, 10**30], invalid=[-1], wrong_type=NOT_INT),
    Sample(numeric.PositiveInt, [1, 10**30], invalid=[0, -1], wrong_type=NOT_INT),
    Sample(numeric.NegativeOrZeroInt, [0, -5], invalid=[1], wrong_type=NOT_INT),
    Sample(numeric.NegativeInt, [-1, -(10**30)], invalid=[0, 1], wrong_type=NOT_INT),
    Sample(
        numeric.Float,
        [0.0, -1.5, 1e300, 5e-324, 3],
        invalid=[float("nan"), float("inf"), 10**400, 2**53 + 1],
        wrong_type=NOT_FLOAT,
        normalized=[(3, "3.0"), (-0.0, "0.0"), (Level.HIGH, "3.0")],
    ),
    Sample(numeric.PositiveOrZeroFloat, [0.0, 2.5], invalid=[-0.1, float("inf")], wrong_type=NOT_FLOAT),
    Sample(numeric.PositiveFloat, [0.1, 2.5], invalid=[0.0, -0.0, -1.0], wrong_type=NOT_FLOAT),
    Sample(numeric.NegativeOrZeroFloat, [0.0, -2.5], invalid=[0.1], wrong_type=NOT_FLOAT),
    Sample(numeric.NegativeFloat, [-0.1, -2.5], invalid=[0.0, -0.0], wrong_type=NOT_FLOAT),
    Sample(
        numeric.DecimalNumber,
        ["1.50", -3, Decimal("1e-30"), 2**100, "9" * 34],
        invalid=["1_000", "١٢", "NaN", "sNaN", "Infinity", "1,5", "", Decimal("NaN")],
        wrong_type=NOT_DECIMAL,
        normalized=[(" 4.10 ", "4.10"), ("-0.00", "0.00"), (Decimal("-0"), "0"), ("1e3", "1E+3"), (Level.HIGH, "3")],
    ),
    Sample(numeric.PositiveOrZeroDecimal, ["0", "1.5"], invalid=["-0.01"], wrong_type=NOT_DECIMAL),
    Sample(numeric.PositiveDecimal, ["0.01", 7], invalid=["0", "-0", "-1"], wrong_type=NOT_DECIMAL),
    Sample(numeric.NegativeOrZeroDecimal, ["0", "-1.5"], invalid=["0.01"], wrong_type=NOT_DECIMAL),
    Sample(numeric.NegativeDecimal, ["-0.01", -7], invalid=["0", "-0.00", "1"], wrong_type=NOT_DECIMAL),
]
