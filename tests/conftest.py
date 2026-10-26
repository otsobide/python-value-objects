"""Shared test setup: hypothesis profiles, the hostile decimal context every test runs under, shared fixtures."""

import decimal
import os
import sys
from collections.abc import Iterator

import pytest
from hypothesis import settings

settings.register_profile("dev", max_examples=100)
settings.register_profile("ci", max_examples=1000, derandomize=True, deadline=None)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))

HOSTILE = decimal.Context(prec=3, rounding=decimal.ROUND_FLOOR, traps=[])


@pytest.fixture(autouse=True)
def hostile_decimal_context() -> Iterator[None]:
    """The library must never depend on the caller's thread-local decimal context."""
    with decimal.localcontext(HOSTILE):
        yield


@pytest.fixture
def int_digit_limit() -> Iterator[int]:
    """Pins the int-to-str digit limit to its default, whatever PYTHONINTMAXSTRDIGITS says; restores it after."""
    before = sys.get_int_max_str_digits()
    sys.set_int_max_str_digits(4300)
    yield 4300
    sys.set_int_max_str_digits(before)
