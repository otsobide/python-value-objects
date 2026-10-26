"""Behaviour every value object must have, driven by tests.samples.SAMPLES. Add one Sample per new VO."""

from __future__ import annotations

import copy
import datetime
import decimal
import importlib
import ipaddress
import pickle
import sys
import uuid
from dataclasses import FrozenInstanceError
from typing import Any

import pytest

import pyvalueobjects as vo
from tests.samples import SAMPLES, Args, Sample
from tests.test_core import CORE_SAMPLES

# The modules whose __all__ the package root re-exports; each family joins when its names are exported.
FAMILIES = ("_core",)
EVAL_NS = {**vars(vo), "Decimal": decimal.Decimal, "datetime": datetime, "uuid": uuid, "ipaddress": ipaddress}
# The public value objects, plus the core's throwaway ones, so the contract runs before any family registers.
CONTRACTED = [*SAMPLES, *CORE_SAMPLES]


def cases(attr: str) -> list[Any]:
    return [pytest.param(s, raw, id=f"{s.id}-{raw!r}"[:80]) for s in CONTRACTED for raw in getattr(s, attr)]


def eval_ns(cls: type) -> dict[str, Any]:
    """EVAL_NS over the namespace of the module that declares cls, so reprs of VOs declared in tests evaluate."""
    return {**vars(sys.modules[cls.__module__]), **EVAL_NS}


def test_every_public_value_object_has_samples() -> None:
    exported = [getattr(vo, name) for name in vo.__all__]
    public = {c for c in exported if isinstance(c, type) and issubclass(c, vo.ValueObject) and not c._abstract}
    assert public - {s.cls for s in SAMPLES} == set()


def test_top_level_all_is_the_union_of_the_family_modules() -> None:
    names = {name for family in FAMILIES for name in importlib.import_module(f"pyvalueobjects.{family}").__all__}
    assert sorted(vo.__all__) == sorted(names)


@pytest.mark.parametrize("sample", CONTRACTED, ids=lambda s: s.id)
def test_samples_are_distinct(sample: Sample) -> None:
    built = [sample.build(raw) for raw in sample.valid]
    assert len(set(built)) == len(built) >= 2


@pytest.mark.parametrize(("sample", "raw"), cases("valid"))
class TestValid:
    def test_equal_and_same_hash(self, sample: Sample, raw: Any) -> None:
        a, b = sample.build(raw), sample.build(raw)
        assert a == b and hash(a) == hash(b) and a is not b

    def test_never_equal_to_other_types(self, sample: Sample, raw: Any) -> None:
        a = sample.build(raw)
        subclass = type("Sub", (sample.cls,), {})  # same value, different concrete type
        assert a != subclass(*a._astuple())
        assert a != object() and a != a._astuple()[0] and a != str(a)

    def test_immutable_without_dict(self, sample: Sample, raw: Any) -> None:
        a = sample.build(raw)
        for name in [*a._fields, *a.__match_args__, "other"]:
            with pytest.raises(AttributeError):
                setattr(a, name, None)
        with pytest.raises(FrozenInstanceError):
            delattr(a, a._fields[0])
        assert not hasattr(a, "__dict__")

    def test_rebuild_from_fields_is_idempotent(self, sample: Sample, raw: Any) -> None:
        a = sample.build(raw)
        assert sample.cls(*a._astuple()) == a and a.replace() == a

    @pytest.mark.parametrize("protocol", range(pickle.HIGHEST_PROTOCOL + 1))
    def test_pickle_roundtrip(self, sample: Sample, raw: Any, protocol: int) -> None:
        a = sample.build(raw)
        restored = pickle.loads(pickle.dumps(a, protocol))
        assert restored == a and type(restored) is type(a)

    def test_copy_is_identity(self, sample: Sample, raw: Any) -> None:
        a = sample.build(raw)
        assert copy.copy(a) is a and copy.deepcopy(a) is a

    def test_repr_evaluates_back(self, sample: Sample, raw: Any) -> None:
        a = sample.build(raw)
        assert eval(repr(a), eval_ns(sample.cls)) == a  # our own repr: safe to evaluate

    def test_str_and_format(self, sample: Sample, raw: Any) -> None:
        a = sample.build(raw)
        assert f"{a}" == str(a)
        if sample.str_roundtrip:
            assert type(a).from_str(str(a)) == a  # type: ignore[attr-defined]

    def test_optional_and_valid(self, sample: Sample, raw: Any) -> None:
        args = raw if isinstance(raw, Args) else (raw,)
        assert sample.cls.from_optional(*[None] * len(args)) is None
        assert sample.cls.from_optional(*args) == sample.build(raw)
        assert sample.cls.is_valid(*args)

    def test_truthy_and_reflexive_order(self, sample: Sample, raw: Any) -> None:
        a = sample.build(raw)
        assert bool(a) is True and a <= a and a >= a and not a < a
        with pytest.raises(TypeError):
            _ = a < object()

    def test_match_args(self, sample: Sample, raw: Any) -> None:
        a = sample.build(raw)
        assert tuple(getattr(a, name) for name in a.__match_args__) == a._astuple()


@pytest.mark.parametrize(("sample", "raw"), cases("invalid"))
def test_invalid_values_rejected(sample: Sample, raw: Any) -> None:
    with pytest.raises(vo.ValueObjectError) as info:
        sample.build(raw)
    assert isinstance(info.value, ValueError) and not isinstance(info.value, vo.InvalidTypeError)
    assert info.value.vo is sample.cls and str(info.value).startswith(f"{sample.cls.__name__}: ")
    assert not sample.cls.is_valid(*(raw if isinstance(raw, Args) else (raw,)))


@pytest.mark.parametrize(("sample", "raw"), cases("wrong_type"))
def test_wrong_types_rejected(sample: Sample, raw: Any) -> None:
    with pytest.raises(vo.InvalidTypeError) as info:
        sample.build(raw)
    assert isinstance(info.value, TypeError) and isinstance(info.value, ValueError)


@pytest.mark.parametrize(("sample", "pair"), cases("normalized"))
def test_normalization(sample: Sample, pair: tuple[Any, str]) -> None:
    raw, expected = pair
    assert str(sample.build(raw)) == expected
