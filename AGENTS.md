# AGENTS.md

This file provides guidance to AI coding agents working with code in this repository.

## Project

`pyvalueobjects` is a dependency-free Python library of validated value objects, published to PyPI. Packaging metadata and the version live in `setup.cfg` (`pyproject.toml` only declares the setuptools build backend). The primary repository is on Codeberg; GitHub is a mirror.

## Commands

```bash
make test                                            # python -m unittest discover -s ./tests -p '*_test.py'
python -m unittest tests.numbers.positive_int_test   # one file
python -m unittest tests.numbers.positive_int_test.TestPositiveIntValueObject.test_zero_value_raises_error  # one test
```

- Test files are named `*_test.py` (not `test_*.py`), so the `-p '*_test.py'` pattern is required; plain `python -m unittest` or default pytest discovery won't find them. Every test subdirectory needs an `__init__.py`.
- There are no runtime dependencies (`requirements.txt` is empty), no linter/formatter config, and `make` / `make build` are no-ops.
- CI (`.github/workflows/tests.yml`) runs `make test` on Python 3.9–3.13, so code must stay 3.9-compatible (e.g. `list[T]` / `X | None` annotations need `from __future__ import annotations`, as in `pyvalueobjects/lists/`).

## Architecture

**Validation chain.** `ValueObject.__init__` (`pyvalueobjects/abstract/valueobject.py`) calls `self._validate(value)` and then stores `_value`. Every subclass overrides `_validate` and calls `super()._validate(value)` first, so constraints accumulate through inheritance:

- `Int` → `PositiveOrZeroInt` → `PositiveInt`; `Int` → `NegativeOrZeroInt` → `NegativeInt`
- `String` → `NonEmptyString` → `Uuid4`, `Cve`, `Cpe` and the other `security/` types; `String` → `IsoDate`

Type checks are strict (`type(value) != int`), so `bool` and subclasses are rejected. Conversions go through classmethods (`Int.from_str`, `Int.from_float`) that build with `cls(...)`, so they work for every `Int` subclass. Regex-based types keep a class-private compiled `__MATCHER` and raise `ValueObjectError` on mismatch.

**Equality and hashing** are value-based, not type-based: `Int(1) == PositiveInt(1)` is `True`, and comparing against a non-`ValueObject` (`Int(1) == 1`) raises `ValueObjectError` instead of returning `False`.

**Nullable variants.** `build_nullable(cls)` (`pyvalueobjects/abstract/nullablevalueobject.py`) returns a subclass whose `__init__` sets `_value = None` and skips validation when given `None`. Each `NullableX` lives in its own `nullable_x.py` module as `_nullable_cls = build_nullable(X)` followed by `class NullableX(_nullable_cls)` with a `value=None` default.

**Lists.** `ArrayList(cls)` and `NullableArrayList(cls)` are factory functions that return a new class, used as `ArrayList(Int)([1, 2])`. Elements are validated by constructing `cls(element)` for each item.

**Public API.** Users import everything from `pyvalueobjects/__init__.py`. `nullable_positive_int.py` and `nullable_negative_int.py` import their base class via `from pyvalueobjects import ...`, which only works because `__init__.py` imports the base before the nullable variant; keep that ordering, or use full submodule imports in new code.

Adding a value object touches: its module plus the `nullable_` counterpart, the export in `__init__.py`, `tests/<category>/<name>_test.py`, and a README section. `EmailAddress`, `Ipv4`, `Ipv6`, `MacAddress`, `Md5Hash`, `Sha256Hash`, `Url` and their nullable variants exist in `pyvalueobjects/security/` but are currently not exported, tested, or documented.

## Tests

Tests use `unittest`. Most suites set `self._cls` in `__init__` and cover hash/equality, `value()`, and error cases with `assertRaises(ValueObjectError, ...)`; nullable suites repeat the base suite and add a `None` case.
