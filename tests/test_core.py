"""The core machinery of pyvalueobjects._core, exercised on throwaway value objects."""

from __future__ import annotations

import abc
import copy
import pickle
from collections.abc import Callable
from dataclasses import FrozenInstanceError
from typing import Any

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
    ValueObject,
    ValueObjectError,
    ValueObjectMeta,
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


# ------------------------------------------------------------------------------------------- ValueObject
# Throwaway composites, declared at module level so that they pickle by reference.


class Point(ValueObject):
    __slots__ = ("x", "y")
    x: int
    y: int

    def __init__(self, x: int, y: int) -> None:
        if type(x) is not int or type(y) is not int:
            raise InvalidTypeError("coordinates must be int", vo=type(self), value=(x, y))
        self._set(x=x, y=y)


class Point3(Point):
    __slots__ = ("z",)
    z: int

    def __init__(self, x: int, y: int, z: int) -> None:
        super().__init__(x, y)
        self._set(z=z)


class Label(ValueObject):
    __slots__ = ("text",)
    text: str

    def __init__(self, text: str) -> None:
        if type(text) is not str:
            raise InvalidTypeError(f"text must be str, got {type(text).__name__}", vo=type(self), value=text)
        self._set(text=text)


class UserId(Label):
    pass


class OrderId(Label):
    pass


class Secret(ValueObject):
    """A private field `_token`, read through the property `token`."""

    __slots__ = ("_token",)
    _token: str

    def __init__(self, token: str) -> None:
        self._set(_token=token)

    @property
    def token(self) -> str:
        return self._token


class Version(Label):
    """Orders numerically by a custom _order_key, not by the text."""

    def _order_key(self) -> Any:
        return tuple(int(part) for part in self.text.split("."))


class Headless(ValueObject):
    """A composite that forgot to define __init__."""

    __slots__ = ("a",)


class Base(ValueObject, abstract=True):
    pass


class Concrete(Base):
    def __init__(self) -> None:
        pass


VALUE_OBJECTS = [Point(1, 2), Point3(1, 2, 3), Label("a"), UserId("u"), OrderId("u"), Secret("s"), Version("1.10")]


@pytest.fixture(params=VALUE_OBJECTS, ids=repr)
def obj(request: pytest.FixtureRequest) -> ValueObject:
    return request.param  # type: ignore[no-any-return]


def test_metaclass_is_an_abc_meta() -> None:
    assert type(ValueObject) is ValueObjectMeta and issubclass(ValueObjectMeta, abc.ABCMeta)


def test_metaclass_gives_slots_to_classes_that_declare_none() -> None:
    assert UserId.__dict__["__slots__"] == () and Point.__dict__["__slots__"] == ("x", "y")
    dynamic = type("Dynamic", (Label,), {})
    assert dynamic.__dict__["__slots__"] == () and not hasattr(dynamic("x"), "__dict__")


def test_value_objects_combine_with_abc() -> None:
    class Shape(ValueObject, abc.ABC):
        @abc.abstractmethod
        def area(self) -> int: ...

    class Square(Shape):
        __slots__ = ("side",)

        def __init__(self, side: int) -> None:
            self._set(side=side)

        def area(self) -> int:
            return self.side**2  # type: ignore[no-any-return]

    class Unfinished(Shape):
        def __init__(self) -> None:
            pass

    assert Square(3).area() == 9
    with pytest.raises(TypeError, match=r"^Can.t instantiate abstract class Unfinished"):
        Unfinished()  # type: ignore[abstract]


@pytest.mark.parametrize(
    ("cls", "fields", "match_args"),
    [
        (Point, ("x", "y"), ("x", "y")),
        (Point3, ("x", "y", "z"), ("x", "y", "z")),  # inherited fields first, in declaration order
        (UserId, ("text",), ("text",)),
        (Secret, ("_token",), ("token",)),  # a private slot is matched by its public name
    ],
)
def test_fields_and_match_args_come_from_the_slots(
    cls: type[ValueObject], fields: tuple[str, ...], match_args: tuple[str, ...]
) -> None:
    assert cls._fields == fields and cls.__match_args__ == match_args


def test_dunder_slots_are_not_fields() -> None:
    class Weak(ValueObject):
        __slots__ = ("a", "__weakref__")

        def __init__(self, a: int) -> None:
            self._set(a=a)

    assert Weak._fields == ("a",) and repr(Weak(1)) == "Weak(1)"


def test_match_by_position_and_keyword() -> None:
    match Point3(1, 2, 3):
        case Point3(1, y, z=3):
            assert y == 2
        case _:
            pytest.fail("Point3 did not match")
    match Secret("abc"):
        case Secret(token):
            assert token == "abc"
        case _:
            pytest.fail("Secret did not match")


@pytest.mark.parametrize("cls", [ValueObject, Headless])
def test_value_object_without_its_own_init_cannot_be_built(cls: type[ValueObject]) -> None:
    with pytest.raises(TypeError, match=f"^{cls.__name__} is abstract: subclass it and define __init__$"):
        cls()


def test_abstract_flag_is_set_per_class() -> None:
    assert ValueObject._abstract and Base._abstract
    assert not Concrete._abstract and not Point._abstract and not UserId._abstract


def test_regression_C03_fields_cannot_be_assigned_or_deleted(obj: ValueObject) -> None:
    """C03 (#33): `vo._value = 'abc'` replaced a validated value, and `del vo._value` worked."""
    before = obj._astuple()
    for name in [*obj._fields, *obj.__match_args__]:
        with pytest.raises(FrozenInstanceError, match=f"cannot assign '{name}'"):
            setattr(obj, name, "abc")
        with pytest.raises(FrozenInstanceError, match=f"cannot delete '{name}'"):
            delattr(obj, name)
    assert obj._astuple() == before


def test_regression_C03_no_attribute_can_be_added(obj: ValueObject) -> None:
    """C03 (#33): `vo.extra = 5` was accepted. There is no __dict__, so not even object.__setattr__ can add one."""
    with pytest.raises(FrozenInstanceError):
        obj.extra = 5  # type: ignore[attr-defined]
    with pytest.raises(AttributeError):
        object.__setattr__(obj, "extra", 5)
    assert not hasattr(obj, "__dict__") and not hasattr(obj, "extra")


def test_regression_C03_init_cannot_run_again_on_a_live_object() -> None:
    """C03 (#33): `p.__init__(2)` changed a set member in place, so the set could no longer find it."""
    point, label = Point3(1, 2, 3), UserId("u")
    members = {point, label}
    with pytest.raises(FrozenInstanceError, match="cannot initialize 'x' again: Point3 is immutable"):
        point.__init__(7, 8, 9)  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError, match="cannot initialize 'text' again"):
        label.__init__("v")  # type: ignore[misc]
    assert point._astuple() == (1, 2, 3) and label.text == "u"
    assert point in members and label in members


def test_failed_construction_raises_in_the_name_of_the_class() -> None:
    with pytest.raises(InvalidTypeError, match=r"^Point: coordinates must be int$") as info:
        Point(1, "2")  # type: ignore[arg-type]
    assert info.value.vo is Point and info.value.value == (1, "2")


def test_always_truthy() -> None:
    assert bool(Label("")) is True and bool(Point(0, 0)) is True


def test_repr_lists_the_fields() -> None:
    assert [repr(obj) for obj in VALUE_OBJECTS] == [
        "Point(1, 2)",
        "Point3(1, 2, 3)",
        "Label('a')",
        "UserId('u')",
        "OrderId('u')",
        "Secret('s')",
        "Version('1.10')",
    ]
