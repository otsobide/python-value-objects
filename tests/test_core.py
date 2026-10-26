"""The core machinery of pyvalueobjects._core, exercised on throwaway value objects."""

from __future__ import annotations

import abc
import copy
import datetime
import decimal
import enum
import math
import operator
import pickle
import re
import sys
import unittest
from collections.abc import Callable, Iterator
from dataclasses import FrozenInstanceError, dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Any
from unittest import mock

import pytest
from hypothesis import given
from hypothesis import strategies as st

import pyvalueobjects
from pyvalueobjects._core import (
    Bounded,
    Bounds,
    CurrencyMismatchError,
    InvalidFormatError,
    InvalidTypeError,
    OutOfRangeError,
    PrecisionError,
    Scalar,
    Sized,
    ValueObject,
    ValueObjectError,
    ValueObjectMeta,
    binary_op,
    check_range,
    literal,
    show,
    unary_op,
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


HUGE = 10**5000  # 5001 digits: more than the default sys.get_int_max_str_digits() of 4300


@pytest.fixture
def int_digit_limit() -> Iterator[int]:
    """Pins the int-to-str digit limit to its default, whatever PYTHONINTMAXSTRDIGITS says."""
    before = sys.get_int_max_str_digits()
    sys.set_int_max_str_digits(4300)
    yield 4300
    sys.set_int_max_str_digits(before)


@pytest.mark.usefixtures("int_digit_limit")
@pytest.mark.parametrize(
    ("value", "shown"),
    [(HUGE, "<int with 16610 bits>"), (-HUGE, "<negative int with 16610 bits>")],
    ids=["positive", "negative"],
)
def test_show_gives_the_size_of_an_int_too_long_for_repr(value: int, shown: str) -> None:
    with pytest.raises(ValueError, match="Exceeds the limit"):
        repr(value)
    assert show(value) == shown


def test_show_lets_other_repr_errors_through() -> None:
    class Broken:
        def __repr__(self) -> str:
            raise ValueError("broken repr")

    with pytest.raises(ValueError, match=r"^broken repr$"):
        show(Broken())


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


class Tag(ValueObject):
    __slots__ = "name"  # a single string declares one slot
    name: str

    def __init__(self, name: str) -> None:
        self._set(name=name)


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


VALUE_OBJECTS = [Point(1, 2), Point3(1, 2, 3), Label("a"), UserId("u"), OrderId("u"), Tag("t"), Secret("s")]
VALUE_OBJECTS += [Version("1.10")]


@pytest.fixture(params=VALUE_OBJECTS, ids=repr)
def obj(request: pytest.FixtureRequest) -> ValueObject:
    return request.param  # type: ignore[no-any-return]


def test_metaclass_is_an_abc_meta() -> None:
    assert type(ValueObject) is ValueObjectMeta and issubclass(ValueObjectMeta, abc.ABCMeta)


def test_metaclass_gives_slots_to_classes_that_declare_none() -> None:
    assert UserId.__dict__["__slots__"] == () and Point.__dict__["__slots__"] == ("x", "y")
    dynamic = type("Dynamic", (Label,), {})
    assert dynamic.__dict__["__slots__"] == () and not hasattr(dynamic("x"), "__dict__")


class Greeter:
    """A plain mixin without __slots__."""

    def greet(self) -> str:
        return "hi"


@pytest.mark.parametrize(
    ("bases", "namespace"),
    [((Greeter, Label), {}), ((Label, Greeter), {}), ((Label,), {"__slots__": ("__dict__",)})],
    ids=["mixin-first", "mixin-last", "dict-slot"],
)
def test_a_class_whose_instances_would_have_a_dict_is_rejected(
    bases: tuple[type, ...], namespace: dict[str, Any]
) -> None:
    """Review of #40: a mixin without __slots__ gave instances a __dict__, so `vo.__dict__["x"] = 1` added state."""
    with pytest.raises(
        TypeError, match=r"^Leaky: instances would have a __dict__; give every base class __slots__ = \(\)$"
    ):
        type("Leaky", bases, namespace)


def test_a_mixin_with_empty_slots_is_accepted() -> None:
    class Polite:
        __slots__ = ()

        def greet(self) -> str:
            return "hi"

    class Greeting(Polite, Label):
        pass

    assert Greeting("a").greet() == "hi" and not hasattr(Greeting("a"), "__dict__")


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
        (Tag, ("name",), ("name",)),  # regression (review of #40): a string __slots__ gave ('n', 'a', 'm', 'e')
    ],
)
def test_fields_and_match_args_come_from_the_slots(
    cls: type[ValueObject], fields: tuple[str, ...], match_args: tuple[str, ...]
) -> None:
    assert cls._fields == fields and cls.__match_args__ == match_args


def test_a_string_slot_is_one_field() -> None:
    """Review of #40: iterating `__slots__ = "name"` gave one field per character, so ==, hash and repr raised."""
    tag = Tag("t")
    assert tag == Tag("t") and tag != Tag("u") and hash(tag) == hash(Tag("t")) and repr(tag) == "Tag('t')"
    assert tag.replace(name="u") == Tag("u") and pickle.loads(pickle.dumps(tag)) == tag


def test_dunder_slots_are_not_fields() -> None:
    class Weak(ValueObject):
        __slots__ = ("a", "__weakref__")

        def __init__(self, a: int) -> None:
            self._set(a=a)

    assert Weak._fields == ("a",) and repr(Weak(1)) == "Weak(1)"


@pytest.mark.parametrize("slot", ["__token", "__token__"])
def test_a_slot_with_two_leading_underscores_is_rejected(slot: str) -> None:
    """Review of #40: a name-mangled slot `__token` was silently left out of the fields, so == and hash ignored it."""
    with pytest.raises(
        TypeError, match=f"^Hidden: slot '{slot}' cannot be a field: a private field takes one underscore$"
    ):

        class Hidden(ValueObject):
            __slots__ = ("a", slot)


def test_a_declared_match_args_must_agree_with_the_slots() -> None:
    """Review of #40: a different __match_args__ was silently replaced, although replace() passes fields in its order."""
    with pytest.raises(
        TypeError, match=r"^Swapped: __match_args__ must be \('a', 'b'\), the fields in order, got \('b', 'a'\)$"
    ):

        class Swapped(ValueObject):
            __slots__ = ("a", "b")
            __match_args__ = ("b", "a")


def test_a_declared_match_args_that_agrees_is_kept() -> None:
    """Spelled out for type checkers, as Scalar does."""

    class Spelled(ValueObject):
        __slots__ = ("a", "_b")
        __match_args__ = ("a", "b")

    assert Spelled.__match_args__ == ("a", "b") and Spelled._fields == ("a", "_b")


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
    assert point in members and label in members and Point3(1, 2, 3) in members


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
        "Tag('t')",
        "Secret('s')",
        "Version('1.10')",
    ]


def test_equal_when_same_type_and_fields(obj: ValueObject) -> None:
    twin = type(obj)(*obj._astuple())
    assert twin == obj and hash(twin) == hash(obj) and twin is not obj and (twin != obj) is False


def test_hash_is_the_hash_of_the_type_and_the_fields(obj: ValueObject) -> None:
    """Spec 2.1. Review of #40: dropping the type from the hash survived every other test."""
    assert hash(obj) == hash((type(obj), obj._astuple()))


def test_hash_differs_between_types_with_the_same_fields() -> None:
    assert hash(UserId("u")) != hash(OrderId("u")) and hash(Label("u")) != hash(UserId("u"))


def test_different_fields_are_not_equal() -> None:
    assert Point(1, 2) != Point(2, 1) and Point3(1, 2, 3) != Point3(1, 2, 4) and Label("a") != Label("A")


@given(st.integers(), st.integers(), st.integers(), st.integers())
def test_equality_hash_and_order_follow_the_fields(a: int, b: int, c: int, d: int) -> None:
    first, second = Point(a, b), Point(c, d)
    assert (first == second) is ((a, b) == (c, d))
    assert (first < second) is ((a, b) < (c, d)) and (first >= second) is ((a, b) >= (c, d))
    if first == second:
        assert hash(first) == hash(second)


@pytest.mark.parametrize(
    "other",
    [None, 1, "a", ("a",), ["a"], object(), mock.sentinel.value],
    ids=["None", "int", "str", "tuple", "list", "object", "sentinel"],
)
def test_regression_C00_comparing_with_a_non_value_object_is_false(other: object) -> None:
    """C00 (#33): `vo == None`, `1 == vo` and `vo != None` raised ValueObjectError instead of answering."""
    label = Label("a")
    assert (label == other) is False and (other == label) is False
    assert (label != other) is True and (other != label) is True


def test_regression_C00_value_objects_mix_with_raw_values_in_containers() -> None:
    """C00 (#33): `in`, dict/set lookups and list methods crashed on a raw value before the match."""
    label = Label("a")
    mixed = [1, None, "a", label]
    assert label in mixed and mixed.index(label) == 3 and mixed.count(label) == 1
    mixed.remove(label)
    assert mixed == [1, None, "a"]
    assert len({label, 1, "a"}) == 3 and label not in {1: 0, "a": 1}

    class SameHash:  # a raw key whose hash collides, so the dict has to call __eq__
        def __hash__(self) -> int:
            return hash(label)

    assert label not in {SameHash(): 0} and SameHash() not in {label: 0}


def test_regression_C00_entities_with_an_optional_value_object_compare() -> None:
    """C00 (#33): frozen-dataclass entities with an optional VO field crashed on ==."""

    @dataclass(frozen=True)
    class Order:
        quantity: Label | None

    assert Order(Label("a")) != Order(None) and Order(Label("a")) == Order(Label("a"))
    assert len({Order(Label("a")), Order(None), Order(Label("a"))}) == 2


def test_regression_C00_unittest_and_mock_assertions_work() -> None:
    """C00 (#33): assertNotEqual and mock.assert_called_with raised ValueObjectError, `vo == ANY` too."""
    case = unittest.TestCase()  # the unittest assertions are the subject here, hence the PT009 waivers
    case.assertNotEqual(Label("a"), None)  # noqa: PT009
    case.assertIn(Label("a"), [None, Label("a")])  # noqa: PT009
    with pytest.raises(AssertionError):
        case.assertEqual(Label("a"), "a")  # noqa: PT009
    called = mock.Mock()
    called(Label("a"))
    called.assert_called_with(Label("a"))
    with pytest.raises(AssertionError):
        called.assert_called_with("a")
    assert Label("a") == mock.ANY


def test_regression_X00_sibling_types_with_the_same_value_differ() -> None:
    """X00 (#33): UserId(x) == OrderId(x), so a dict keyed by UserId answered an OrderId lookup."""
    assert UserId("u") != OrderId("u") and (UserId("u") == OrderId("u")) is False
    assert {UserId("u"): "user"}.get(OrderId("u")) is None
    assert len({UserId("u"), OrderId("u"), UserId("u")}) == 2


@pytest.mark.parametrize(("parent", "child"), [(Label("u"), UserId("u")), (Label("1.0"), Version("1.0"))])
def test_regression_X00_parent_and_child_types_with_the_same_value_differ(parent: Label, child: Label) -> None:
    """X00 (#33): equality ignored the type, also between a class and its subclass (Int(1) == PositiveInt(1))."""
    assert parent != child and child != parent and len({parent, child}) == 2


def test_ordering_within_one_type() -> None:
    assert sorted([Point(2, 0), Point(1, 5), Point(1, 2)]) == [Point(1, 2), Point(1, 5), Point(2, 0)]
    assert Point(1, 2) <= Point(1, 2) and Point(1, 2) >= Point(1, 2) and not Point(1, 2) < Point(1, 2)
    assert Point(1, 2) < Point(1, 3) and Point(1, 3) > Point(1, 2) and not Point(1, 3) <= Point(1, 2)
    assert max(Label("a"), Label("b")) == Label("b")


def test_ordering_uses_the_order_key() -> None:
    assert Version("1.9") < Version("1.10") and Label("1.9") > Label("1.10")
    assert sorted([Version("1.10"), Version("1.9"), Version("0.99")]) == [
        Version("0.99"),
        Version("1.9"),
        Version("1.10"),
    ]


@pytest.mark.parametrize("op", [operator.lt, operator.le, operator.gt, operator.ge])
@pytest.mark.parametrize(
    ("left", "right"),
    [(Label("a"), "a"), ("a", Label("a")), (Label("a"), None), (UserId("u"), OrderId("u")), (Label("u"), UserId("u"))],
)
def test_ordering_against_another_type_raises_type_error(
    op: Callable[[object, object], bool], left: object, right: object
) -> None:
    with pytest.raises(TypeError, match="not supported between instances"):
        op(left, right)


def test_repr_evaluates_back(obj: ValueObject) -> None:
    assert eval(repr(obj), globals()) == obj  # our own repr: safe to evaluate


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_pickle_round_trip(obj: ValueObject, protocol: int) -> None:
    restored = pickle.loads(pickle.dumps(obj, protocol))
    assert restored == obj and type(restored) is type(obj) and restored is not obj


def test_unpickling_validates_again() -> None:
    class Tampered:
        def __reduce__(self) -> tuple[Any, ...]:
            return (Point, ("1", 2))

    with pytest.raises(InvalidTypeError, match=r"^Point: coordinates must be int$"):
        pickle.loads(pickle.dumps(Tampered()))


def test_copies_are_the_object_itself(obj: ValueObject) -> None:
    assert copy.copy(obj) is obj and copy.deepcopy(obj) is obj
    holder = [obj, {"key": obj}]
    cloned = copy.deepcopy(holder)
    assert cloned is not holder and cloned[0] is obj and cloned[1]["key"] is obj  # type: ignore[index]


# ------------------------------------------------------------------------------------------- replace, optional values, components


class Even(ValueObject):
    __slots__ = ("n",)
    n: int

    def __init__(self, n: int) -> None:
        if n % 2:
            raise OutOfRangeError(f"n must be even, got {n}", vo=type(self), value=n)
        self._set(n=n)


class Unchecked(Even):
    """A subclass that skips its parent's check, so rebuilding it as the parent fails."""

    def __init__(self, n: int) -> None:
        self._set(n=n)


class LooseLabel(Label):
    def __init__(self, text: Any) -> None:
        self._set(text=text)


class Parcel(ValueObject):
    __slots__ = ("label", "origin")
    label: Label
    origin: Point

    def __init__(self, label: Label, origin: Point) -> None:
        cls = type(self)
        self._set(label=cls._component("label", Label, label), origin=cls._component("origin", Point, origin))


def test_replace_changes_the_named_fields_only() -> None:
    point = Point3(1, 2, 3)
    assert point.replace(z=9) == Point3(1, 2, 9) and point.replace(x=0, y=0) == Point3(0, 0, 3)
    assert point == Point3(1, 2, 3)  # the original is untouched
    assert point.replace() == point and type(UserId("u").replace(text="v")) is UserId


def test_replace_uses_the_public_name_of_a_private_field() -> None:
    assert Secret("a").replace(token="b") == Secret("b")
    with pytest.raises(TypeError, match=r"^Secret has no field\(s\) \['_token'\]$"):
        Secret("a").replace(_token="b")


def test_replace_rejects_unknown_fields() -> None:
    with pytest.raises(TypeError, match=r"^Point has no field\(s\) \['v', 'w'\]$"):
        Point(1, 2).replace(w=1, v=2, x=3)


def test_replace_validates_again() -> None:
    with pytest.raises(InvalidTypeError, match=r"^Point: coordinates must be int$"):
        Point(1, 2).replace(x="3")
    assert Parcel(Label("a"), Point(0, 0)).replace(label=UserId("b")).label.__class__ is Label


@given(st.integers(), st.integers(), st.integers())
def test_replace_matches_a_fresh_construction(x: int, y: int, new_y: int) -> None:
    assert Point(x, y).replace(y=new_y) == Point(x, new_y)


@pytest.mark.skipif(sys.version_info < (3, 13), reason="copy.replace() exists from Python 3.13 on")
def test_copy_replace_uses_replace() -> None:
    assert copy.replace(Point(1, 2), y=5) == Point(1, 5)  # type: ignore[attr-defined]
    with pytest.raises(TypeError, match="has no field"):
        copy.replace(Point(1, 2), w=5)  # type: ignore[attr-defined]


@pytest.mark.parametrize(("cls", "nulls"), [(Label, 1), (UserId, 1), (Point, 2), (Point3, 3)])
def test_from_optional_gives_none_when_every_argument_is_none(cls: type[ValueObject], nulls: int) -> None:
    assert cls.from_optional(*[None] * nulls) is None


@pytest.mark.parametrize(
    ("cls", "args"), [(Label, ("a",)), (UserId, ("u",)), (Point, (1, 2)), (Point3, (1, 2, 3)), (Secret, ("s",))]
)
def test_from_optional_builds_from_values(cls: type[ValueObject], args: tuple[Any, ...]) -> None:
    built = cls.from_optional(*args)
    assert built == cls(*args) and type(built) is cls


@pytest.mark.parametrize("args", [(1, None), (None, 2)])
def test_from_optional_rejects_a_partly_null_composite(args: tuple[Any, ...]) -> None:
    with pytest.raises(InvalidTypeError, match=r"^Point: coordinates must be int$"):
        Point.from_optional(*args)


def test_from_optional_without_arguments_is_a_call_error() -> None:
    with pytest.raises(TypeError, match="missing 2 required positional arguments"):
        Point.from_optional()


@pytest.mark.parametrize(
    ("cls", "nulls", "message"),
    [
        (Point, 1, "missing a required argument: 'y'"),
        (Point, 3, "too many positional arguments"),
        (Label, 2, "too many positional arguments"),
        (Point3, 2, "missing a required argument: 'z'"),
    ],
)
def test_from_optional_with_the_wrong_number_of_nulls_is_a_call_error(
    cls: type[ValueObject], nulls: int, message: str
) -> None:
    """Review of #40: Point.from_optional(None) returned None, so a forgotten column failed only on a non-NULL row."""
    with pytest.raises(TypeError, match=rf"^{cls.__name__}\.from_optional\(\): {message}$") as info:
        cls.from_optional(*[None] * nulls)
    assert not isinstance(info.value, ValueObjectError) and info.value.__cause__ is None


def test_from_optional_follows_the_constructor_signature() -> None:
    class Weight(ValueObject):
        __slots__ = ("amount", "unit")

        def __init__(self, amount: int, unit: str = "kg") -> None:
            self._set(amount=amount, unit=unit)

    assert Weight.from_optional(None) is None and Weight.from_optional(None, None) is None
    assert Weight.from_optional(5) == Weight(5, "kg")
    with pytest.raises(TypeError, match=r"^Weight\.from_optional\(\): too many positional arguments$"):
        Weight.from_optional(None, None, None)


@pytest.mark.parametrize(
    ("cls", "args", "valid"),
    [
        (Label, ("a",), True),
        (Label, (1,), False),  # InvalidTypeError
        (Even, (2,), True),
        (Even, (3,), False),  # OutOfRangeError
        (Point, (1, 2), True),
        (Point, (1, None), False),
    ],
)
def test_is_valid_reports_validation_errors(cls: type[ValueObject], args: tuple[Any, ...], valid: bool) -> None:
    assert cls.is_valid(*args) is valid


@pytest.mark.parametrize(("cls", "args"), [(Point, (1,)), (Label, ("a", "b")), (ValueObject, ()), (Headless, ())])
def test_is_valid_does_not_hide_misuse(cls: type[ValueObject], args: tuple[Any, ...]) -> None:
    with pytest.raises(TypeError) as info:
        cls.is_valid(*args)
    assert not isinstance(info.value, ValueObjectError)


def test_component_keeps_an_instance_of_exactly_the_kind() -> None:
    label, origin = Label("a"), Point(1, 2)
    parcel = Parcel(label, origin)
    assert parcel.label is label and parcel.origin is origin


def test_component_rebuilds_a_subclass_instance_as_the_kind() -> None:
    parcel = Parcel(UserId("u"), Point(1, 2))
    assert type(parcel.label) is Label and parcel.label == Label("u")
    assert parcel == Parcel(Label("u"), Point(1, 2)) and parcel == Parcel(OrderId("u"), Point(1, 2))


def test_component_rebuilds_a_subclass_with_extra_fields_from_the_kind_fields() -> None:
    """Review of #40: the rebuild passed every field of the subclass, so Point(1, 2, 3) raised a bare TypeError."""
    parcel = Parcel(Label("a"), Point3(1, 2, 3))
    assert type(parcel.origin) is Point and parcel.origin == Point(1, 2)
    assert parcel == Parcel(Label("a"), Point(1, 2)) and Parcel.is_valid(Label("a"), Point3(1, 2, 3))


@pytest.mark.parametrize(
    ("label", "origin", "message"),
    [
        ("a", Point(1, 2), "label must be Label, got str"),
        (None, Point(1, 2), "label must be Label, got NoneType"),
        (Label("a"), (1, 2), "origin must be Point, got tuple"),
        (Label("a"), Label("a"), "origin must be Point, got Label"),
    ],
)
def test_component_requires_an_instance_for_a_composite(label: Any, origin: Any, message: str) -> None:
    with pytest.raises(InvalidTypeError, match=f"^Parcel: {message}$") as info:
        Parcel(label, origin)
    assert info.value.vo is Parcel and info.value.value in (label, origin) and info.value.__cause__ is None


@pytest.mark.parametrize(
    ("kind", "raw", "error", "reason", "value"),
    [
        (Label, LooseLabel(5), InvalidTypeError, "label: text must be str, got int", 5),
        (Even, Unchecked(3), OutOfRangeError, "count: n must be even, got 3", 3),
    ],
)
def test_component_relabels_errors_with_the_composite_and_field_name(
    kind: type[ValueObject], raw: ValueObject, error: type[ValueObjectError], reason: str, value: object
) -> None:
    name = reason.split(":")[0]
    with pytest.raises(error) as info:
        Parcel._component(name, kind, raw)
    err = info.value
    assert type(err) is error and str(err) == f"Parcel: {reason}"
    assert (err.reason, err.vo, err.value) == (reason, Parcel, value)
    assert isinstance(err.__cause__, error) and err.__cause__.vo is kind


# ------------------------------------------------------------------------------------------- Scalar


class Count(Scalar[int]):
    accepts = (int,)
    _parse_str = staticmethod(int)


class Small(Count):
    @classmethod
    def _validate(cls, value: int) -> int:
        value = super()._validate(value)
        if value > 9:
            raise OutOfRangeError(f"value must be <= 9, got {value}", vo=cls, value=value)
        return value


class Ratio(Scalar[float]):
    accepts = (float, int)
    _parse_str = staticmethod(float)

    @classmethod
    def _convert(cls, raw: float) -> float:
        return float(raw)


class Code(Scalar[str]):
    """Normalizes to upper case, then requires ASCII letters."""

    accepts = (str,)

    @classmethod
    def _validate(cls, value: str) -> str:
        value = super()._validate(value).strip().upper()
        if not (value.isascii() and value.isalpha()):
            raise InvalidFormatError(f"expected letters, got {show(value)}", vo=cls, value=value)
        return value


class ShortCode(Code):
    @classmethod
    def _validate(cls, value: str) -> str:
        value = super()._validate(value)  # the parent normalizes first, so the stripped text is measured
        if len(value) > 3:
            raise OutOfRangeError(f"length must be <= 3, got {len(value)}", vo=cls, value=value)
        return value


class Hex(Scalar[int]):
    """Takes an int or hexadecimal text; str() is the hexadecimal text, so repr() shows it too."""

    accepts = (int, str)

    @classmethod
    def _convert(cls, raw: int | str) -> int:
        return int(raw, 16) if isinstance(raw, str) else raw

    def __str__(self) -> str:
        return format(self._value, "x")


class Day(Scalar[datetime.date]):
    accepts = (datetime.date,)
    _parse_str = staticmethod(datetime.date.fromisoformat)


class Reciprocal(Scalar[Fraction]):
    """Not a lawful scalar (it does not accept its own stored type): only for the ArithmeticError case."""

    accepts = (int,)

    @classmethod
    def _convert(cls, raw: int) -> Fraction:
        return 1 / Fraction(raw)


class Status(enum.IntEnum):
    ACTIVE = 1


class Shade(enum.StrEnum):
    RED = "red"


class Loud(str):
    def __str__(self) -> str:
        return "LOUD"


class Heavy(float):
    pass


class Liar(int):
    def __int__(self) -> int:
        return 42


class Broken(int):
    def __int__(self) -> Any:
        return "not an int"


class Sinker(float):
    def __float__(self) -> float:
        return 99.0


class Tagged(ValueObject):
    __slots__ = ("code", "count")
    code: Code
    count: Count

    def __init__(self, code: Any, count: Any) -> None:
        cls = type(self)
        self._set(code=cls._component("code", Code, code), count=cls._component("count", Count, count))


SCALARS = [Count(0), Count(-7), Count(2**100), Small(3), Ratio(0.5), Ratio(2), Code(" ab "), ShortCode("x")]
SCALARS += [Hex(255), Hex("10"), Day(datetime.date(2024, 2, 29))]
SCALAR_EVAL = {**globals(), "datetime": datetime}


@pytest.fixture(params=SCALARS, ids=repr)
def scalar(request: pytest.FixtureRequest) -> Scalar[Any]:
    return request.param  # type: ignore[no-any-return]


def test_scalar_fields_and_match_args() -> None:
    assert Count._fields == ("_value",) and Count.__match_args__ == ("value",) and Day.__match_args__ == ("value",)
    match Count(5):
        case Count(5):
            pass
        case _:
            pytest.fail("Count(5) did not match")


class AbstractCode(Code, abstract=True):
    pass


@pytest.mark.parametrize("cls", [Scalar, AbstractCode])
def test_abstract_scalars_cannot_be_built(cls: type[Scalar[Any]]) -> None:
    with pytest.raises(TypeError, match=f"^{cls.__name__} is abstract: subclass it$"):
        cls("x")


@pytest.mark.parametrize(
    ("cls", "raw", "value"),
    [
        (Count, 5, 5),
        (Count, 2**200, 2**200),
        (Ratio, 2, 2.0),
        (Ratio, -0.5, -0.5),
        (Code, " ab ", "AB"),
        (Hex, "ff", 255),
        (Hex, 16, 16),
        (Day, datetime.date(2024, 2, 29), datetime.date(2024, 2, 29)),
    ],
)
def test_value_is_the_converted_and_normalized_input(cls: type[Scalar[Any]], raw: Any, value: Any) -> None:
    built = cls(raw)
    assert built.value == value and type(built.value) is type(value)


@pytest.mark.parametrize(
    ("cls", "raw", "expected"),
    [
        (Count, "1", "expected int, got str"),
        (Count, 1.0, "expected int, got float"),
        (Count, None, "expected int, got NoneType"),
        (Count, True, "expected int, got bool"),  # bool is never an int
        (Count, False, "expected int, got bool"),
        (Count, Fraction(1), "expected int, got Fraction"),
        (Hex, True, "expected int or str, got bool"),
        (Ratio, True, "expected float or int, got bool"),
        (Ratio, "1", "expected float or int, got str"),
        (Code, b"x", "expected str, got bytes"),
        (Code, Status.ACTIVE, "expected str, got Status"),  # an enum of a type that is not accepted
        (Count, Shade.RED, "expected int, got Shade"),
        (Day, datetime.datetime(2024, 1, 1), "expected date, got datetime"),  # a datetime is never a date
        (Count, Point(1, 2), "expected int, got Point"),  # composites are not unwrapped
    ],
)
def test_type_gate_rejects_types_not_accepted(cls: type[Scalar[Any]], raw: Any, expected: str) -> None:
    with pytest.raises(InvalidTypeError, match=f"^{cls.__name__}: {expected}$") as info:
        cls(raw)
    assert info.value.vo is cls and info.value.value is raw and info.value.reason == expected


@pytest.mark.parametrize(
    ("cls", "raw", "value"),
    [
        (Count, Status.ACTIVE, 1),
        (Ratio, Status.ACTIVE, 1.0),
        (Ratio, Heavy(1.5), 1.5),
        (Code, Shade.RED, "RED"),
        (Code, Loud("q"), "Q"),  # the str value, not the overridden __str__
        (Count, Liar(5), 5),  # regression (review of #40): the int value, not the overridden __int__
        (Count, Broken(5), 5),  # ... whose non-int result used to raise a bare TypeError
        (Ratio, Liar(5), 5.0),
        (Ratio, Sinker(1.5), 1.5),  # the float value, not the overridden __float__
    ],
)
def test_instances_of_int_float_str_subclasses_become_the_plain_type(
    cls: type[Scalar[Any]], raw: Any, value: Any
) -> None:
    built = cls(raw)
    assert built.value == value and type(built.value) is type(value) and built == cls(value)


@pytest.mark.parametrize(
    ("cls", "raw", "expected"),
    [
        (Count, Count(3), Count(3)),
        (Count, Small(3), Count(3)),
        (Small, Count(3), Small(3)),
        (Ratio, Count(2), Ratio(2.0)),
        (Count, Hex("ff"), Count(255)),
        (Code, ShortCode("ab"), Code("AB")),
    ],
)
def test_another_scalar_is_unwrapped(cls: type[Scalar[Any]], raw: Scalar[Any], expected: Scalar[Any]) -> None:
    built = cls(raw)
    assert built == expected and type(built) is cls


@pytest.mark.parametrize(
    ("cls", "raw", "error", "message"),
    [
        (Small, Count(12), OutOfRangeError, "Small: value must be <= 9, got 12"),
        (Count, Ratio(1.5), InvalidTypeError, "Count: expected int, got float"),
        (ShortCode, Code("abcd"), OutOfRangeError, "ShortCode: length must be <= 3, got 4"),
    ],
)
def test_an_unwrapped_value_obeys_the_target_rules(
    cls: type[Scalar[Any]], raw: Scalar[Any], error: type[ValueObjectError], message: str
) -> None:
    with pytest.raises(error) as info:
        cls(raw)
    assert str(info.value) == message and info.value.vo is cls


@pytest.mark.parametrize(
    ("cls", "raw", "cause"),
    [(Hex, "zz", ValueError), (Hex, "", ValueError), (Reciprocal, 0, ZeroDivisionError)],
)
def test_convert_errors_become_invalid_format_errors(cls: type[Scalar[Any]], raw: Any, cause: type[Exception]) -> None:
    with pytest.raises(InvalidFormatError, match=f"^{cls.__name__}: cannot parse {show(raw)}$") as info:
        cls(raw)
    assert type(info.value) is InvalidFormatError and info.value.value == raw
    assert type(info.value.__cause__) is cause


def test_value_object_errors_from_convert_pass_through_unchanged() -> None:
    raised = OutOfRangeError("too big", value=1)

    class Strict(Scalar[int]):
        accepts = (int,)

        @classmethod
        def _convert(cls, raw: int) -> int:
            raise raised

    with pytest.raises(OutOfRangeError) as info:
        Strict(1)
    assert info.value is raised and info.value.__cause__ is None


def test_other_exceptions_from_convert_are_not_validation_errors() -> None:
    class Buggy(Scalar[int]):
        accepts = (int,)

        @classmethod
        def _convert(cls, raw: int) -> int:
            raise KeyError(raw)

    with pytest.raises(KeyError):
        Buggy(1)


@pytest.mark.parametrize(
    ("raw", "error", "message"),
    [
        (" abcd ", OutOfRangeError, "ShortCode: length must be <= 3, got 4"),
        ("a1", InvalidFormatError, "ShortCode: expected letters, got 'A1'"),  # the parent check names the subclass
    ],
)
def test_validate_chain_runs_the_parent_first(raw: str, error: type[ValueObjectError], message: str) -> None:
    assert ShortCode(" ab ").value == "AB"
    with pytest.raises(error) as info:
        ShortCode(raw)
    assert str(info.value) == message and info.value.vo is ShortCode


@pytest.mark.parametrize("name", ["value", "_value"])
def test_value_is_read_only(name: str) -> None:
    count = Count(1)
    with pytest.raises(FrozenInstanceError):
        setattr(count, name, 2)
    assert count.value == 1


def test_regression_C03_scalar_init_cannot_run_again_on_a_live_object() -> None:
    """C03 (#33): `PositiveInt(1).__init__(2)` changed a set member in place."""
    count = Count(1)
    members = {count}
    with pytest.raises(FrozenInstanceError, match=r"^cannot initialize '_value' again: Count is immutable$"):
        count.__init__(2)  # type: ignore[misc]
    assert count.value == 1 and count in members and Count(1) in members


def test_idempotence_law(scalar: Scalar[Any]) -> None:
    """Every scalar accepts its own stored type, so rebuilding from .value or from itself gives an equal object."""
    cls = type(scalar)
    assert cls(scalar.value) == scalar and cls(scalar) == scalar and cls(*scalar._astuple()) == scalar


def test_scalar_round_trips(scalar: Scalar[Any]) -> None:
    cls = type(scalar)
    for protocol in PROTOCOLS:
        assert pickle.loads(pickle.dumps(scalar, protocol)) == scalar
    assert copy.copy(scalar) is scalar and copy.deepcopy(scalar) is scalar
    assert eval(repr(scalar), SCALAR_EVAL) == scalar  # our own repr: safe to evaluate
    assert cls.from_str(str(scalar)) == scalar
    assert scalar.replace(value=scalar.value) == scalar and cls.from_optional(scalar.value) == scalar
    assert cls.from_optional(None) is None and cls.is_valid(scalar.value)


@pytest.mark.parametrize("nulls", [2, 3])
def test_scalar_from_optional_takes_one_argument(nulls: int) -> None:
    """Review of #40: Count.from_optional(None, None) returned None instead of refusing the extra argument."""
    with pytest.raises(TypeError, match=r"^Count\.from_optional\(\): too many positional arguments$"):
        Count.from_optional(*[None] * nulls)
    with pytest.raises(TypeError, match="takes 2 positional arguments but 3 were given"):
        Count.from_optional(1, None)


def test_scalars_equal_only_within_one_type() -> None:
    assert Count(1) == Count(1) and Count(1) != Small(1) and Count(1) != Ratio(1) and Count(1) != Hex(1)
    assert Count(1) != 1 and Code("ab") != "AB" and len({Count(1), Small(1), Hex(1), Count(1)}) == 3
    assert Count(1) < Count(2) and Code("b") > Code("a")
    with pytest.raises(TypeError):
        _ = Count(1) < Small(2)


@given(st.integers())
def test_int_scalar_properties(number: int) -> None:
    count = Count(number)
    assert count.value == number and str(count) == str(number) and repr(count) == f"Count({number!r})"
    assert Count.from_str(str(number)) == count and Count(count) == count and hash(count) == hash(Count(number))


@given(st.text())
def test_is_valid_agrees_with_construction(text: str) -> None:
    normalized = text.strip().upper()
    assert Code.is_valid(text) is (normalized.isascii() and normalized.isalpha())


@pytest.mark.parametrize(
    ("cls", "text", "expected"),
    [
        (Count, "12", Count(12)),
        (Count, " -7 ", Count(-7)),  # whatever _parse_str accepts
        (Small, "3", Small(3)),
        (Ratio, "0.25", Ratio(0.25)),
        (Day, "2024-02-29", Day(datetime.date(2024, 2, 29))),
        (Code, " ab ", Code("AB")),  # no _parse_str: the constructor takes the text
        (Hex, "ff", Hex(255)),
    ],
)
def test_from_str(cls: type[Scalar[Any]], text: str, expected: Scalar[Any]) -> None:
    built = cls.from_str(text)
    assert built == expected and type(built) is cls


@pytest.mark.parametrize(
    ("cls", "text", "error", "message"),
    [
        (Count, "x", InvalidFormatError, "Count: cannot parse 'x'"),
        (Count, "", InvalidFormatError, "Count: cannot parse ''"),
        (Day, "2024-02-30", InvalidFormatError, "Day: cannot parse '2024-02-30'"),
        (Small, "12", OutOfRangeError, "Small: value must be <= 9, got 12"),  # parsed, then validated
        (Code, "a1", InvalidFormatError, "Code: expected letters, got 'A1'"),
    ],
)
def test_from_str_errors(cls: type[Scalar[Any]], text: str, error: type[ValueObjectError], message: str) -> None:
    with pytest.raises(error) as info:
        cls.from_str(text)
    assert type(info.value) is error and str(info.value) == message and info.value.vo is cls


@pytest.mark.parametrize("text", [12, None, b"12", ["12"]])
def test_from_str_takes_only_text(text: Any) -> None:
    with pytest.raises(InvalidTypeError, match=f"^Count: from_str expects str, got {type(text).__name__}$") as info:
        Count.from_str(text)
    assert info.value.value is text


class Digit(enum.StrEnum):
    ONE = "1"


class Echo(Scalar[str]):
    """Stores the type and the text its parser was given."""

    accepts = (str,)
    _parse_str = staticmethod(lambda text: f"{type(text).__name__}:{text}")


@pytest.mark.parametrize(
    ("cls", "text", "expected"),
    [
        (Count, Digit.ONE, Count(1)),
        (Code, Shade.RED, Code("RED")),  # no _parse_str: the constructor gets the plain text
        (Code, Loud("ab"), Code("AB")),  # the str value, not the overridden __str__
        (Echo, Shade.RED, Echo("str:red")),  # the parser gets a plain str
        (Echo, Loud("ab"), Echo("str:ab")),
    ],
)
def test_from_str_reads_a_str_subclass_as_its_plain_value(
    cls: type[Scalar[Any]], text: str, expected: Scalar[Any]
) -> None:
    """Review of #40: from_str refused StrEnum members, which the constructor of a str scalar accepts."""
    built = cls.from_str(text)
    assert built == expected and type(built) is cls and type(built.value) is type(expected.value)


def test_from_str_of_a_scalar_that_takes_no_text() -> None:
    class Plain(Scalar[float]):
        accepts = (float,)

    with pytest.raises(InvalidTypeError, match=r"^Plain: expected float, got str$"):
        Plain.from_str("1.5")


@pytest.mark.parametrize(
    ("built", "text", "shown"),
    [
        (Count(5), "5", "Count(5)"),
        (Ratio(2), "2.0", "Ratio(2.0)"),
        (Code(" ab "), "AB", "Code('AB')"),  # str is accepted: repr shows the text
        (Hex(255), "ff", "Hex('ff')"),  # ... as str() writes it
        (Day(datetime.date(2024, 2, 29)), "2024-02-29", "Day(datetime.date(2024, 2, 29))"),
    ],
)
def test_str_and_repr(built: Scalar[Any], text: str, shown: str) -> None:
    assert (str(built), repr(built), f"{built}", format(built, "")) == (text, shown, text, text)


@pytest.mark.parametrize(
    ("built", "spec", "text"),
    [
        (Count(5), "03d", "005"),
        (Count(1234567), ",", "1,234,567"),
        (Ratio(0.5), ".2%", "50.00%"),
        (Code("ab"), ">4", "  AB"),
        (Hex(255), "d", "255"),  # a spec formats the value, not str()
        (Hex(255), "#x", "0xff"),
        (Day(datetime.date(2024, 2, 29)), "%d/%m", "29/02"),
    ],
)
def test_format_spec_formats_the_value(built: Scalar[Any], spec: str, text: str) -> None:
    assert format(built, spec) == text and f"{built:{spec}}" == text


@pytest.mark.parametrize(
    ("code", "count", "expected"),
    [
        (" ab ", 2, Tagged(Code("AB"), Count(2))),
        (Code("ab"), Count(2), Tagged(Code("AB"), Count(2))),
        (ShortCode("ab"), Small(2), Tagged(Code("AB"), Count(2))),  # rebuilt as the field type
        ("ab", Hex("ff"), Tagged(Code("AB"), Count(255))),  # another scalar converts by unwrapping
        (Shade.RED, Status.ACTIVE, Tagged(Code("RED"), Count(1))),
    ],
)
def test_component_converts_scalar_fields(code: Any, count: Any, expected: Tagged) -> None:
    tagged = Tagged(code, count)
    assert tagged == expected and type(tagged.code) is Code and type(tagged.count) is Count


@pytest.mark.parametrize(
    ("code", "count", "error", "reason", "value"),
    [
        (" 1 ", 2, InvalidFormatError, "code: expected letters, got '1'", "1"),
        (None, 2, InvalidTypeError, "code: expected str, got NoneType", None),
        ("ab", "2", InvalidTypeError, "count: expected int, got str", "2"),
        ("ab", Ratio(1.5), InvalidTypeError, "count: expected int, got float", 1.5),
    ],
)
def test_component_relabels_scalar_errors(
    code: Any, count: Any, error: type[ValueObjectError], reason: str, value: object
) -> None:
    with pytest.raises(error) as info:
        Tagged(code, count)
    err = info.value
    assert type(err) is error and str(err) == f"Tagged: {reason}" and (err.vo, err.value) == (Tagged, value)
    assert type(err.__cause__) is error and err.__cause__.vo in (Code, Count)


# ------------------------------------------------------------------------------------------- literal()

INTEGER = literal(re.compile(r"[+-]?[0-9]+"), int)
ISO_DATE = literal(re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}"), datetime.date.fromisoformat)


class Whole(Scalar[int]):
    accepts = (int,)
    _parse_str = staticmethod(INTEGER)


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("42", 42),
        ("-7", -7),
        ("+7", 7),
        ("007", 7),
        ("-0", 0),
        (" 12 ", 12),  # surrounding ASCII whitespace is stripped
        ("\t12\n", 12),
        ("\r\n\v\f12\f\v\r\n", 12),
        ("9007199254740993", 9007199254740993),  # exact: never goes through float
        (str(2**200), 2**200),
    ],
)
def test_literal_accepts_the_grammar(text: str, value: int) -> None:
    assert INTEGER(text) == value and type(INTEGER(text)) is int


ASCII_WHITESPACE = " \t\n\r\f\v"
# Unicode whitespace that str.strip() would remove; regression (review of #40): they were stripped around a literal.
UNICODE_SPACES = ["\u00a0", "\u3000", "\u2028", "\u0085", "\x1c", "\x1f"]


@pytest.mark.parametrize(
    "text",
    [
        *["", " ", "1_000", "١٢", "１２", "0x10", "1.0", "1e3", "nan", "1 2", "12\n3", "--1", "+", "²"],
        *[f"{space}42" for space in UNICODE_SPACES],
        *[f"42{space}" for space in UNICODE_SPACES],
        " \u00a042\u00a0 ",
    ],
)
def test_literal_rejects_text_outside_the_grammar(text: str) -> None:
    with pytest.raises(ValueError, match=r"^not a valid literal: ") as info:
        INTEGER(text)
    assert str(info.value) == f"not a valid literal: {text.strip(ASCII_WHITESPACE)!r}"


def test_literal_does_not_convert_rejected_text() -> None:
    convert = mock.Mock(return_value=1)
    parse = literal(re.compile(r"[0-9]+"), convert)
    with pytest.raises(ValueError, match="not a valid literal"):
        parse("1_0")
    convert.assert_not_called()
    assert parse(" 10 ") == 1
    convert.assert_called_once_with("10")  # the stripped text


@pytest.mark.parametrize("loose", ["20240131", "2024-W05-3", "2024W053"])
def test_literal_pins_the_grammar_whatever_the_converter_accepts(loose: str) -> None:
    assert datetime.date.fromisoformat(loose) == datetime.date(2024, 1, 31)  # the converter alone takes it
    assert ISO_DATE(" 2024-01-31 ") == datetime.date(2024, 1, 31)
    with pytest.raises(ValueError, match="not a valid literal"):
        ISO_DATE(loose)


TOO_MANY_DIGITS = "1" * 4301  # int() refuses it under the default digit limit, which int_digit_limit pins


@pytest.mark.usefixtures("int_digit_limit")
@pytest.mark.parametrize(
    ("parse", "text"),
    [(ISO_DATE, "2024-02-30"), (INTEGER, TOO_MANY_DIGITS)],
    ids=["impossible-day", "too-many-digits"],
)
def test_literal_lets_converter_errors_through(parse: Callable[[str], Any], text: str) -> None:
    """The text matches the grammar, so the error is the converter's (an impossible day, too many digits)."""
    with pytest.raises(ValueError, match=r"^(?!not a valid literal)"):  # any message but the grammar's
        parse(text)


@given(st.integers())
def test_literal_round_trips_every_int(number: int) -> None:
    assert INTEGER(str(number)) == number and INTEGER(f" {number:+d} ") == number


@given(st.text(st.characters(categories=["Nd"]), min_size=1))
def test_literal_accepts_only_ascii_digits(digits: str) -> None:
    if digits.isascii():
        assert INTEGER(digits) == int(digits)
    else:
        with pytest.raises(ValueError, match="not a valid literal"):
            INTEGER(digits)


@pytest.mark.parametrize(("text", "value"), [("9007199254740993", 9007199254740993), (" -12 ", -12)])
def test_literal_as_parse_str(text: str, value: int) -> None:
    assert Whole.from_str(text) == Whole(value)


@pytest.mark.usefixtures("int_digit_limit")
@pytest.mark.parametrize(
    "text",
    ["1_000", "١٢", "1.0", "", TOO_MANY_DIGITS],
    ids=["underscore", "arabic", "float", "empty", "too-many-digits"],
)
def test_literal_errors_become_invalid_format_errors_in_from_str(text: str) -> None:
    with pytest.raises(InvalidFormatError, match=f"^Whole: cannot parse {re.escape(show(text))}$") as info:
        Whole.from_str(text)
    assert type(info.value.__cause__) is ValueError and info.value.value == text


# ------------------------------------------------------------------------------------------- constraints


@pytest.mark.parametrize(
    ("measured", "bounds", "message"),
    [
        (1, {"gt": 0}, None),
        (0, {"gt": 0}, "value must be > 0, got 0"),
        (0, {"ge": 0}, None),
        (-1, {"ge": 0}, "value must be >= 0, got -1"),
        (9, {"lt": 10}, None),
        (10, {"lt": 10}, "value must be < 10, got 10"),
        (10, {"le": 10}, None),
        (11, {"le": 10}, "value must be <= 10, got 11"),
        (5, {"gt": 0, "ge": 1, "lt": 10, "le": 9}, None),
        (-1, {"gt": 0, "ge": 1, "lt": 10, "le": 9}, "value must be > 0, got -1"),  # checked in gt, ge, lt, le order
        (0.5, {"ge": 1, "le": 0}, "value must be >= 1, got 0.5"),
        (99, {}, None),
        (Decimal("0.10"), {"gt": Decimal("0.1")}, "value must be > 0.1, got Decimal('0.10')"),
        (Fraction(1, 3), {"le": Fraction(1, 4)}, "value must be <= 1/4, got Fraction(1, 3)"),
        (
            datetime.date(2024, 1, 1),
            {"ge": datetime.date(2024, 1, 2)},
            "value must be >= 2024-01-02, got datetime.date(2024, 1, 1)",
        ),
        (datetime.timedelta(0), {"gt": datetime.timedelta(0)}, "value must be > 0:00:00, got datetime.timedelta(0)"),
        ("b", {"lt": "b"}, "value must be < b, got 'b'"),
    ],
)
def test_check_range(measured: Any, bounds: dict[str, Any], message: str | None) -> None:
    if message is None:
        check_range(Thing, measured, **bounds)
        return
    with pytest.raises(OutOfRangeError) as info:
        check_range(Thing, measured, **bounds, value="raw")
    err = info.value
    assert type(err) is OutOfRangeError and str(err) == f"Thing: {message}"
    assert (err.reason, err.vo, err.value) == (message, Thing, "raw")


def test_check_range_names_what_it_measures_and_cuts_long_values() -> None:
    long = "x" * 100
    with pytest.raises(OutOfRangeError) as info:
        check_range(Thing, long, le="xxx", what="text")
    assert info.value.reason == f"text must be <= xxx, got {show(long)}" and len(show(long)) == 80
    assert info.value.value is None  # nothing given


@pytest.mark.parametrize("bound", ["gt", "ge", "lt", "le"])
def test_check_range_rejects_nan_for_every_bound(bound: str) -> None:
    with pytest.raises(OutOfRangeError, match=r", got nan$"):
        check_range(Thing, float("nan"), **{bound: 0})


@given(st.integers(), st.integers(), st.integers())
def test_check_range_agrees_with_the_comparisons(measured: int, low: int, high: int) -> None:
    try:
        check_range(Thing, measured, ge=low, le=high)
    except OutOfRangeError:
        assert not low <= measured <= high
    else:
        assert low <= measured <= high


class Age(Bounded[int]):
    accepts = (int,)
    ge = 0
    le = 150


class Adult(Age):
    ge = 18  # overrides one bound, inherits le


class Probability(Bounded[float]):
    accepts = (float, int)
    ge = 0
    le = 1

    @classmethod
    def _convert(cls, raw: float) -> float:
        return float(raw)


class Future(Bounded[datetime.date]):
    accepts = (datetime.date,)
    gt = datetime.date(2026, 1, 1)


class Timeout(Bounded[datetime.timedelta]):
    accepts = (datetime.timedelta,)
    gt = datetime.timedelta(0)
    lt = datetime.timedelta(hours=1)


@pytest.mark.parametrize(
    ("cls", "raw"),
    [
        (Age, 0),
        (Age, 150),
        (Adult, 18),
        (Probability, 0),
        (Probability, 1.0),
        (Future, datetime.date(2026, 1, 2)),
        (Timeout, datetime.timedelta(minutes=59)),
    ],
)
def test_bounded_accepts_values_within_the_bounds(cls: type[Bounded[Any]], raw: Any) -> None:
    assert cls(raw).value == raw


@pytest.mark.parametrize(
    ("cls", "raw", "message"),
    [
        (Age, -1, "Age: value must be >= 0, got -1"),
        (Age, 151, "Age: value must be <= 150, got 151"),
        (Adult, 17, "Adult: value must be >= 18, got 17"),
        (Adult, 151, "Adult: value must be <= 150, got 151"),
        (Probability, 1.5, "Probability: value must be <= 1, got 1.5"),
        (Future, datetime.date(2026, 1, 1), "Future: value must be > 2026-01-01, got datetime.date(2026, 1, 1)"),
        (
            Timeout,
            datetime.timedelta(hours=1),
            "Timeout: value must be < 1:00:00, got datetime.timedelta(seconds=3600)",
        ),
    ],
)
def test_bounded_rejects_values_outside_the_bounds(cls: type[Bounded[Any]], raw: Any, message: str) -> None:
    with pytest.raises(OutOfRangeError) as info:
        cls(raw)
    assert str(info.value) == message and info.value.vo is cls and info.value.value == cls._convert(raw)
    assert not cls.is_valid(raw)


def test_bounded_float_rejects_nan() -> None:
    with pytest.raises(OutOfRangeError, match=r"^Probability: value must be >= 0, got nan$") as info:
        Probability(float("nan"))
    assert math.isnan(info.value.value)  # type: ignore[arg-type]


@pytest.mark.usefixtures("int_digit_limit")
@pytest.mark.parametrize(
    ("cls", "raw", "error", "message"),
    [
        (Age, HUGE, OutOfRangeError, "Age: value must be <= 150, got <int with 16610 bits>"),
        (Age, -HUGE, OutOfRangeError, "Age: value must be >= 0, got <negative int with 16610 bits>"),
        (Ratio, HUGE, InvalidFormatError, "Ratio: cannot parse <int with 16610 bits>"),  # float() overflows
    ],
    ids=["above", "below", "unconvertible"],
)
def test_an_int_too_long_for_repr_still_gives_a_validation_error(
    cls: type[Scalar[Any]], raw: int, error: type[ValueObjectError], message: str
) -> None:
    """Review of #40: building the message called repr() on the int, so a plain ValueError escaped."""
    with pytest.raises(error) as info:
        cls(raw)
    assert type(info.value) is error and str(info.value) == message and info.value.value == raw
    assert cls.is_valid(raw) is False


def test_bounds_run_after_the_type_gate() -> None:
    with pytest.raises(InvalidTypeError, match=r"^Age: expected int, got str$"):
        Age("5")


def test_bounded_keeps_the_scalar_behaviour() -> None:
    assert Adult(Age(30)) == Adult(30) and Age(30) != Adult(30) and Age(20) < Age(30)
    with pytest.raises(OutOfRangeError):
        Adult(Age(10))  # unwrapped, then checked against the target's bounds


class Reading(Bounds, ValueObject):
    """A composite that bounds one of its fields with the Bounds mixin."""

    __slots__ = ("amount", "unit")

    def __init__(self, amount: int, unit: str) -> None:
        type(self)._check_bounds(amount, value=(amount, unit))
        self._set(amount=amount, unit=unit)


class Kelvin(Reading):
    ge = 0


def test_bounds_mixin_on_a_composite() -> None:
    assert Reading(-5, "C").amount == -5 and Kelvin(0, "K") == Kelvin(0, "K")
    with pytest.raises(OutOfRangeError, match=r"^Kelvin: value must be >= 0, got -1$") as info:
        Kelvin(-1, "K")
    assert info.value.value == (-1, "K") and not hasattr(Kelvin(1, "K"), "__dict__")


class Name(Sized[str]):
    accepts = (str,)
    min_length = 1
    max_length = 5


class Trimmed(Name):
    """Normalizes before its parent runs, so the length is measured on the stripped text."""

    @classmethod
    def _validate(cls, value: str) -> str:
        return super()._validate(value.strip())


class Pair(Sized[tuple[int, ...]]):
    accepts = (tuple, list)
    min_length = 2
    max_length = 2

    @classmethod
    def _convert(cls, raw: Any) -> tuple[int, ...]:
        return tuple(raw)


class Anything(Sized[str]):
    accepts = (str,)


@pytest.mark.parametrize(
    ("cls", "raw", "value"),
    [
        (Name, "a", "a"),
        (Name, "abcde", "abcde"),
        (Trimmed, "  ab  ", "ab"),
        (Pair, [1, 2], (1, 2)),
        (Anything, "", ""),
        (Anything, "x" * 10_000, "x" * 10_000),
    ],
)
def test_sized_accepts_lengths_within_the_limits(cls: type[Sized[Any]], raw: Any, value: Any) -> None:
    assert cls(raw).value == value


@pytest.mark.parametrize(
    ("cls", "raw", "message", "value"),
    [
        (Name, "", "Name: length must be >= 1, got 0", ""),
        (Name, "abcdef", "Name: length must be <= 5, got 6", "abcdef"),
        (Trimmed, "   ", "Trimmed: length must be >= 1, got 0", ""),
        (Trimmed, " abcdef ", "Trimmed: length must be <= 5, got 6", "abcdef"),
        (Pair, (1,), "Pair: length must be >= 2, got 1", (1,)),
        (Pair, [1, 2, 3], "Pair: length must be <= 2, got 3", (1, 2, 3)),
    ],
)
def test_sized_rejects_lengths_outside_the_limits(cls: type[Sized[Any]], raw: Any, message: str, value: Any) -> None:
    with pytest.raises(OutOfRangeError) as info:
        cls(raw)
    assert str(info.value) == message and info.value.value == value  # the value itself, not its length


@given(st.text(max_size=8))
def test_sized_is_valid_agrees_with_the_length(text: str) -> None:
    assert Name.is_valid(text) is (1 <= len(text) <= 5)


@pytest.mark.parametrize("cls", [Bounded, Sized])
def test_constraint_bases_are_abstract(cls: type[Scalar[Any]]) -> None:
    with pytest.raises(TypeError, match=f"^{cls.__name__} is abstract"):
        cls(1)


# ------------------------------------------------------------------------------------------- binary_op / unary_op


class Units(Bounded[int]):
    accepts = (int,)
    operand_types = (int,)
    __add__ = binary_op(operator.add)
    __radd__ = binary_op(operator.add, reflected=True)
    __sub__ = binary_op(operator.sub)
    __rsub__ = binary_op(operator.sub, reflected=True)
    __mul__ = binary_op(operator.mul)
    __floordiv__ = binary_op(operator.floordiv)
    __neg__ = unary_op(operator.neg)
    __pos__ = unary_op(operator.pos)
    __abs__ = unary_op(abs)


class PositiveUnits(Units):
    gt = 0


class Real(Scalar[float]):
    accepts = (float, int)
    operand_types = (float, int)
    __pow__ = binary_op(operator.pow)

    @classmethod
    def _convert(cls, raw: float) -> float:
        return float(raw)


class Span(Scalar[datetime.timedelta]):
    accepts = (datetime.timedelta,)
    operand_types = (datetime.timedelta,)
    __add__ = binary_op(operator.add)
    __mul__ = binary_op(operator.mul, operands=(int,), same_type=False)  # Span * count only
    __neg__ = unary_op(operator.neg)
    __abs__ = unary_op(abs)


class Tally(Scalar[int]):
    """No operand_types: only another Tally is a valid operand."""

    accepts = (int,)
    __add__ = binary_op(operator.add)


class Scaled(Scalar[int]):
    """Scaled * int only: same_type=False refuses Scaled * Scaled, and the explicit operands replace
    operand_types, so a float is refused too, although int * int and int * float would both compute."""

    accepts = (int,)
    operand_types = (int, float)
    __mul__ = binary_op(operator.mul, operands=(int,), same_type=False)


TRAPPING = decimal.Context(prec=34, traps=[decimal.InvalidOperation, decimal.DivisionByZero, decimal.Overflow])


class Amount(Scalar[Decimal]):
    """Decimal arithmetic in a context that traps Overflow, as the decimal family does."""

    accepts = (Decimal, int)
    operand_types = (Decimal, int)
    __mul__ = binary_op(TRAPPING.multiply)
    __rmul__ = binary_op(TRAPPING.multiply, reflected=True)
    __pos__ = unary_op(TRAPPING.plus)  # rounds to the context, so an exponent beyond Emax overflows


DAY = datetime.timedelta(days=1)


@pytest.mark.parametrize(
    ("compute", "expected"),
    [
        (lambda: Units(3) + Units(2), Units(5)),
        (lambda: Units(3) + 2, Units(5)),
        (lambda: 2 + Units(3), Units(5)),  # a raw value on the left still gives the VO type
        (lambda: Units(3) - 10, Units(-7)),
        (lambda: 10 - Units(3), Units(7)),  # reflected operands keep their order
        (lambda: Units(-4) * Units(3), Units(-12)),
        (lambda: Units(7) // 2, Units(3)),
        (lambda: Units(-7) // Units(2), Units(-4)),
        (lambda: PositiveUnits(3) + 2, PositiveUnits(5)),  # the left operand's concrete type
        (lambda: 2 + PositiveUnits(3), PositiveUnits(5)),
        (lambda: -Units(3), Units(-3)),
        (lambda: +Units(3), Units(3)),
        (lambda: abs(Units(-3)), Units(3)),
        (lambda: abs(PositiveUnits(3)), PositiveUnits(3)),
        (lambda: Real(2) ** 0.5, Real(2**0.5)),
        (lambda: Span(DAY) + Span(DAY), Span(2 * DAY)),
        (lambda: Span(DAY) * 3, Span(3 * DAY)),
        (lambda: -Span(DAY), Span(-DAY)),
        (lambda: Tally(1) + Tally(2), Tally(3)),
        (lambda: Scaled(2) * 3, Scaled(6)),
        (lambda: Amount(Decimal("1.5")) * 2, Amount(Decimal("3.0"))),
        (lambda: 2 * Amount(Decimal("1.5")), Amount(Decimal("3.0"))),
    ],
)
def test_operators_build_the_left_operand_type(compute: Callable[[], Scalar[Any]], expected: Scalar[Any]) -> None:
    result = compute()
    assert result == expected and type(result) is type(expected)


@pytest.mark.parametrize(
    ("compute", "message"),
    [
        (lambda: PositiveUnits(1) - PositiveUnits(5), "PositiveUnits: value must be > 0, got -4"),
        (lambda: PositiveUnits(1) - 1, "PositiveUnits: value must be > 0, got 0"),
        (lambda: 1 - PositiveUnits(1), "PositiveUnits: value must be > 0, got 0"),
        (lambda: -PositiveUnits(1), "PositiveUnits: value must be > 0, got -1"),
    ],
)
def test_results_are_validated_again(compute: Callable[[], Scalar[Any]], message: str) -> None:
    with pytest.raises(OutOfRangeError) as info:
        compute()
    assert str(info.value) == message and info.value.vo is PositiveUnits


def type_name(obj: object) -> str:
    """The type name an operator TypeError shows: C types outside builtins carry their module (decimal.Decimal)."""
    kind = type(obj)
    return kind.__name__ if kind.__module__ in ("builtins", __name__) else f"{kind.__module__}.{kind.__name__}"


@pytest.mark.parametrize(
    ("left", "right", "symbol"),
    [
        pytest.param(Units(1), 1.5, "+", id="type-outside-operand-types"),
        pytest.param(Units(1), True, "+", id="bool-is-not-int"),  # operand types are exact
        pytest.param(Units(1), "1", "+", id="str"),
        pytest.param(Units(1), Decimal(1), "+", id="decimal"),
        pytest.param(Units(1), PositiveUnits(1), "+", id="child-vo"),  # parent, child and sibling VOs do not mix
        pytest.param(PositiveUnits(1), Units(1), "+", id="parent-vo"),
        pytest.param(Units(1), Tally(1), "+", id="sibling-vo"),
        pytest.param(1.5, Units(1), "+", id="reflected-type-outside-operand-types"),
        pytest.param(Units(1), None, "-", id="none"),
        pytest.param(Span(DAY), Span(DAY), "*", id="same-type-false"),
        pytest.param(Scaled(2), Scaled(3), "*", id="same-type-false-computable"),
        pytest.param(Span(DAY), DAY, "*", id="operands-replace-operand-types"),
        pytest.param(Scaled(2), 1.5, "*", id="operands-replace-operand-types-computable"),
        pytest.param(Span(DAY), 2.5, "*", id="type-outside-operands"),
        pytest.param(Span(DAY), 1, "+", id="type-outside-operand-types-of-another-operator"),
        pytest.param(Tally(1), 1, "+", id="no-operand-types"),  # raw values are refused
    ],
)
def test_other_operands_are_a_type_error(left: object, right: object, symbol: str) -> None:
    """Only the NotImplemented path names the operands' own types: an operand that got through would fail on the
    unwrapped value instead ('int' and 'str', 'timedelta' and 'timedelta') or build a result.

    Regression (review of #40): matching the message prefix let accepted operands pass for the wrong reason.
    """
    message = f"unsupported operand type(s) for {symbol}: '{type_name(left)}' and '{type_name(right)}'"
    with pytest.raises(TypeError, match=f"^{re.escape(message)}$") as info:
        eval(f"left {symbol} right", {"left": left, "right": right})
    assert not isinstance(info.value, ValueObjectError)


@pytest.mark.parametrize("divisor", [0, Units(0)])
def test_division_by_zero_propagates(divisor: object) -> None:
    with pytest.raises(ZeroDivisionError):
        _ = Units(1) // divisor  # type: ignore[operator]


@pytest.mark.parametrize(
    ("compute", "vo", "value"),
    [
        (lambda: Span(datetime.timedelta.max) + DAY, Span, (Span(datetime.timedelta.max), DAY)),
        (lambda: Span(datetime.timedelta.max) * 2, Span, (Span(datetime.timedelta.max), 2)),
        (lambda: Real(1e308) ** 2, Real, (Real(1e308), 2)),
        (lambda: -Span(datetime.timedelta.max), Span, Span(datetime.timedelta.max)),
    ],
)
def test_overflow_becomes_out_of_range_error(compute: Callable[[], Scalar[Any]], vo: type, value: object) -> None:
    with pytest.raises(OutOfRangeError, match=f"^{vo.__name__}: result out of range: ") as info:
        compute()
    assert info.value.vo is vo and info.value.value == value and type(info.value.__cause__) is OverflowError


MAX_AMOUNT, BEYOND_EMAX = Amount(Decimal("9e999999")), Amount(Decimal("1e1000000"))


@pytest.mark.parametrize(
    ("compute", "value"),
    [
        (lambda: MAX_AMOUNT * 10, (MAX_AMOUNT, 10)),
        (lambda: 10 * MAX_AMOUNT, (MAX_AMOUNT, 10)),
        (lambda: MAX_AMOUNT * MAX_AMOUNT, (MAX_AMOUNT, MAX_AMOUNT)),
        (lambda: +BEYOND_EMAX, BEYOND_EMAX),
    ],
    ids=["mul", "rmul", "same-type", "unary"],
)
def test_a_trapped_decimal_overflow_becomes_out_of_range_error(compute: Callable[[], Amount], value: object) -> None:
    """Review of #40: decimal.Overflow is an ArithmeticError but not an OverflowError, so it escaped the helpers."""
    with pytest.raises(OutOfRangeError, match=r"^Amount: result out of range: decimal overflow$") as info:
        compute()
    assert info.value.vo is Amount and info.value.value == value and type(info.value.__cause__) is decimal.Overflow


def test_in_place_operators_rebind_and_never_mutate() -> None:
    total = original = Units(1)
    total += 2
    total *= Units(3)
    assert total == Units(9) and original == Units(1) and original.value == 1


@given(st.integers(), st.integers())
def test_units_arithmetic_matches_int_arithmetic(a: int, b: int) -> None:
    assert (Units(a) + b).value == a + b == (b + Units(a)).value
    assert (Units(a) - Units(b)).value == a - b and (a - Units(b)).value == a - b
    assert (Units(a) * Units(b)).value == a * b and (-Units(a)).value == -a and abs(Units(a)).value == abs(a)


@given(st.integers(1, 10**6), st.integers(1, 10**6))
def test_positive_subtraction_raises_exactly_when_not_positive(a: int, b: int) -> None:
    try:
        result = PositiveUnits(a) - PositiveUnits(b)
    except OutOfRangeError:
        assert a - b <= 0
    else:
        assert result.value == a - b > 0
