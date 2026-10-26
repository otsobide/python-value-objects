# AGENTS.md

This file provides guidance to AI coding agents working with code in this repository.

## Project

`pyvalueobjects` is a dependency-free Python library of validated value objects, published to PyPI. Packaging metadata and the version live only in `pyproject.toml` (PEP 621, setuptools backend). The dev tools (pytest, pytest-cov, hypothesis, mypy, ruff) form the `dev` dependency group, pinned by the committed `uv.lock`. The primary repository is on Codeberg; GitHub is a mirror.

## Commands

```bash
make install                                         # uv sync: .venv with the dev group, as pinned by uv.lock
make test                                            # uv run pytest
uv run pytest tests/test_project.py                  # one file
uv run pytest tests/test_project.py::test_warnings_are_errors   # one test; -k EXPR selects by name
make check                                           # the default goal: lint, typecheck, then cov
make lint                                            # ruff check + ruff format --check
make format                                          # ruff check --fix + ruff format
make typecheck                                       # mypy --strict on pyvalueobjects/
make cov                                             # the suite with branch coverage
make build                                           # sdist and wheel in dist/
make clean                                           # removes build outputs and tool caches
```

- pytest collects the new `test_*.py` modules and the 0.x unittest modules named `*_test.py`. Plain pytest discovery finds both patterns. Only `python -m unittest discover` needs `-p '*_test.py'`, plus `-t .` so that `tests/numbers` does not shadow the stdlib `numbers` module. Every test directory needs an `__init__.py`, so pytest imports its modules as `tests.<dir>.<module>`.
- Warnings are errors. The one exception is a transitional filter for the invalid escape sequences in the legacy `cpe.py`.
- ruff and strict mypy skip the 0.x code (`extend-exclude` for ruff, `exclude` plus `ignore_errors` overrides for mypy, all in `pyproject.toml`). New code must pass `make lint typecheck`. The coverage gate stays at 0 % until the 1.0 core lands.
- CI (`.github/workflows/tests.yml`) runs `uv sync --locked` and `uv run pytest --cov` on Python 3.11–3.15, plus a quality job on 3.11 that runs lint and mypy, builds and `twine check`s the package, and installs the wheel alone. Code must stay 3.11-compatible. After changing dependencies, run `uv lock` and commit `uv.lock`.
- `tests/test_project.py` checks these conventions (metadata, pytest settings, Makefile, CI, this file), so update it together with them.

## Architecture

**Validation chain.** `ValueObject.__init__` (`pyvalueobjects/abstract/valueobject.py`) calls `self._validate(value)` and then stores `_value`. Every subclass overrides `_validate` and calls `super()._validate(value)` first, so constraints accumulate through inheritance:

- `Int` → `PositiveOrZeroInt` → `PositiveInt`; `Int` → `NegativeOrZeroInt` → `NegativeInt`
- `Float` → `PositiveFloat`; `Float` → `NegativeFloat` (`Float` also rejects NaN and infinities)
- `String` → `NonEmptyString` → `Uuid4`, `Cve`, `Cpe` and the other `security/` types; `String` → `IsoDate`

Type checks are strict (`type(value) != int`), so `bool` and subclasses are rejected. Conversions go through classmethods (`Int.from_str`/`from_float`, `Float.from_str`/`from_int`) that build with `cls(...)`, so they work for every subclass. Regex-based types keep a class-private compiled `__MATCHER` and raise `ValueObjectError` on mismatch.

**Equality and hashing** are value-based, not type-based: `Int(1) == PositiveInt(1)` is `True`, and comparing against a non-`ValueObject` (`Int(1) == 1`) raises `ValueObjectError` instead of returning `False`.

**Nullable variants.** `build_nullable(cls)` (`pyvalueobjects/abstract/nullablevalueobject.py`) returns a subclass whose `__init__` sets `_value = None` and skips validation when given `None`. Each `NullableX` lives in its own `nullable_x.py` module as `_nullable_cls = build_nullable(X)` followed by `class NullableX(_nullable_cls)` with a `value=None` default.

**Lists.** `ArrayList(cls)` and `NullableArrayList(cls)` are factory functions that return a new class, used as `ArrayList(Int)([1, 2])`. Elements are validated by constructing `cls(element)` for each item. Generated classes are cached per element type in a module-level dict, so `ArrayList(Int) is ArrayList(Int)` and `isinstance` checks work; `NullableArrayList(Int)` subclasses the cached `ArrayList(Int)`.

**Public API.** Users import everything from `pyvalueobjects/__init__.py`. `nullable_positive_int.py` and `nullable_negative_int.py` import their base class via `from pyvalueobjects import ...`, which only works because `__init__.py` imports the base before the nullable variant; keep that ordering, or use full submodule imports in new code.

Adding a value object touches: its module plus the `nullable_` counterpart, the export in `__init__.py`, `tests/<category>/<name>_test.py`, and a README section. `EmailAddress`, `Ipv4`, `Ipv6`, `MacAddress`, `Md5Hash`, `Sha256Hash`, `Url` and their nullable variants exist in `pyvalueobjects/security/` but are currently not exported, tested, or documented.

## Tests

The 0.x tests use `unittest` and run under pytest; new tests are plain pytest modules. Most 0.x suites set `self._cls` in `__init__` and cover hash/equality, `value()`, and error cases with `assertRaises(ValueObjectError, ...)`; nullable suites repeat the base suite and add a `None` case.
