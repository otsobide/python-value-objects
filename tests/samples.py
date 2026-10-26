"""Registry of inputs per value object, consumed by test_contract.py. One Sample per concrete public VO."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pyvalueobjects as vo


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


# Each family adds a Sample per value object in the commit that adds the value object (B3-B9).
SAMPLES: list[Sample] = []
