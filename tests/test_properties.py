"""Hypothesis properties for the algebra the contract suite cannot express."""

from __future__ import annotations

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pyvalueobjects._core import OutOfRangeError
from pyvalueobjects.numeric import Float, Int, PositiveInt


@given(st.integers(), st.integers())
def test_int_arithmetic_matches_python(a: int, b: int) -> None:
    assert Int(a) + Int(b) == Int(a + b) and Int(a) - b == Int(a - b) and Int(a) * b == Int(a * b)
    assert -Int(a) == Int(-a) and abs(Int(a)) == Int(abs(a)) and a + Int(b) == Int(a + b)


@given(st.integers(), st.integers().filter(bool))
def test_int_floor_division_and_modulo_match_python(a: int, b: int) -> None:
    quotient, remainder = Int(a) // b, Int(a) % Int(b)
    assert (quotient, remainder) == (Int(a // b), Int(a % b)) and quotient.value * b + remainder.value == a


@given(st.integers(1, 10**6), st.integers(1, 10**6))
def test_positive_int_subtraction_raises_exactly_when_not_positive(a: int, b: int) -> None:
    try:
        assert (PositiveInt(a) - PositiveInt(b)).value == a - b > 0
    except OutOfRangeError:
        assert a - b <= 0


@given(st.floats(allow_nan=False, allow_infinity=False), st.floats(allow_nan=False, allow_infinity=False))
def test_float_arithmetic_matches_python_or_leaves_the_finite_range(a: float, b: float) -> None:
    for compute, expected in ((lambda: Float(a) + b, a + b), (lambda: Float(a) * Float(b), a * b)):
        if math.isfinite(expected):
            result = compute().value
            assert result == expected and (result != 0 or math.copysign(1.0, result) == 1.0)  # never -0.0
        else:
            with pytest.raises(OutOfRangeError, match=f"^Float: must be finite, got {expected}$"):
                compute()
