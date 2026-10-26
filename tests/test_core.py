"""The core machinery of pyvalueobjects._core, exercised on throwaway value objects."""

from __future__ import annotations

import copy
import pickle
from collections.abc import Callable

import pytest
from hypothesis import given
from hypothesis import strategies as st

import pyvalueobjects
from pyvalueobjects._core import (
    CurrencyMismatchError,
    InvalidFormatError,
    InvalidTypeError,
    OutOfRangeError,
    PrecisionError,
    ValueObjectError,
    show,
)

PROTOCOLS = range(pickle.HIGHEST_PROTOCOL + 1)

# ------------------------------------------------------------------------------------------- errors

ERRORS = [
    ValueObjectError,
    InvalidTypeError,
    InvalidFormatError,
    PrecisionError,
    OutOfRangeError,
    CurrencyMismatchError,
]


class Thing:
    """A module-level class to name in errors: `.vo` pickles by reference."""


def assert_same_error(clone: ValueObjectError, original: ValueObjectError) -> None:
    assert type(clone) is type(original)
    assert (str(clone), clone.args) == (str(original), original.args)
    assert (clone.reason, clone.vo, clone.value) == (original.reason, original.vo, original.value)


@pytest.mark.parametrize(
    ("error", "bases"),
    [
        (ValueObjectError, (ValueError,)),
        (InvalidTypeError, (ValueObjectError, TypeError)),
        (InvalidFormatError, (ValueObjectError,)),
        (PrecisionError, (InvalidFormatError,)),
        (OutOfRangeError, (ValueObjectError,)),
        (CurrencyMismatchError, (ValueObjectError,)),
    ],
)
def test_error_hierarchy(error: type[ValueObjectError], bases: tuple[type, ...]) -> None:
    assert error.__bases__ == bases


@pytest.mark.parametrize("error", ERRORS)
def test_one_except_value_error_catches_every_error(error: type[ValueObjectError]) -> None:
    with pytest.raises(ValueError, match=r"^Thing: bad$"):
        raise error("bad", vo=Thing)


@pytest.mark.parametrize("error", ERRORS)
def test_only_invalid_type_error_is_also_a_type_error(error: type[ValueObjectError]) -> None:
    assert issubclass(error, TypeError) is (error is InvalidTypeError)


@pytest.mark.parametrize("error", ERRORS)
def test_message_is_class_name_then_reason(error: type[ValueObjectError]) -> None:
    err = error("value must be > 0, got -4", vo=Thing, value=-4)
    assert str(err) == "Thing: value must be > 0, got -4"
    assert err.args == ("Thing: value must be > 0, got -4",)
    assert (err.reason, err.vo, err.value) == ("value must be > 0, got -4", Thing, -4)


@pytest.mark.parametrize("error", ERRORS)
def test_message_without_a_value_object_is_the_reason(error: type[ValueObjectError]) -> None:
    err = error("bad")
    assert (str(err), err.args, err.reason, err.vo, err.value) == ("bad", ("bad",), "bad", None, None)


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("error", ERRORS)
def test_errors_pickle_with_their_attributes(error: type[ValueObjectError], protocol: int) -> None:
    err = error("bad", vo=Thing, value=[1, "x"])
    assert_same_error(pickle.loads(pickle.dumps(err, protocol)), err)


@pytest.mark.parametrize("clone", [copy.copy, copy.deepcopy])
@pytest.mark.parametrize("error", ERRORS)
def test_errors_copy_with_their_attributes(
    error: type[ValueObjectError], clone: Callable[[ValueObjectError], ValueObjectError]
) -> None:
    err = error("bad", vo=Thing, value=(1, 2))
    assert_same_error(clone(err), err)


def test_regression_C06_keyword_construction_keeps_the_message() -> None:
    """C06 (#33): the 0.x error never called super().__init__, so keyword construction gave str() == ''."""
    err = ValueObjectError(reason="boom", vo=Thing, value=1)
    assert (str(err), err.args) == ("Thing: boom", ("Thing: boom",))
    assert str(ValueObjectError(reason="boom")) == "boom"


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_regression_C06_keyword_built_errors_pickle_and_copy(protocol: int) -> None:
    """C06 (#33): rebuilding the 0.x error called ValueObjectError() without its message and raised TypeError."""
    for err in (ValueObjectError(reason="boom"), OutOfRangeError(reason="boom", vo=Thing, value=-1)):
        for clone in (pickle.loads(pickle.dumps(err, protocol)), copy.copy(err), copy.deepcopy(err)):
            assert_same_error(clone, err)


def test_the_root_and_the_legacy_module_export_the_core_error() -> None:
    """0.x code raises the core error, so its failures are ValueErrors too. Delete the legacy part with _legacy/."""
    from pyvalueobjects._legacy.errors.ValueObjectError import ValueObjectError as LegacyError
    from pyvalueobjects._legacy.numbers.int import Int as LegacyInt

    assert pyvalueobjects.ValueObjectError is LegacyError is ValueObjectError
    with pytest.raises(ValueError, match=r"^Input type should be: int\.$") as info:
        LegacyInt("1")
    assert type(info.value) is ValueObjectError


@pytest.mark.parametrize(
    ("value", "shown"),
    [
        ("x", "'x'"),
        (None, "None"),
        (-4, "-4"),
        ("a" * 78, "'" + "a" * 78 + "'"),  # 80 characters: kept
        ("a" * 79, "'" + "a" * 76 + "..."),  # 81 characters: cut to 80
        (list(range(40)), repr(list(range(40)))[:77] + "..."),
    ],
)
def test_show_is_a_repr_cut_to_80_characters(value: object, shown: str) -> None:
    assert show(value) == shown


@given(st.one_of(st.text(), st.integers(), st.lists(st.integers()), st.binary()))
def test_show_never_exceeds_80_characters_and_keeps_the_repr_prefix(value: object) -> None:
    text, shown = repr(value), show(value)
    assert len(shown) <= 80
    assert shown == (text if len(text) <= 80 else text[:77] + "...")
