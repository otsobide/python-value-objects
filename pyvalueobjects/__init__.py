"""Validated, immutable value objects for domain-driven design. Zero runtime dependencies."""

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
)
from pyvalueobjects.numeric import (
    DECIMAL_CONTEXT,
    DecimalNumber,
    Float,
    Int,
    NegativeDecimal,
    NegativeFloat,
    NegativeInt,
    NegativeOrZeroDecimal,
    NegativeOrZeroFloat,
    NegativeOrZeroInt,
    Numeric,
    Percentage,
    PositiveDecimal,
    PositiveFloat,
    PositiveInt,
    PositiveOrZeroDecimal,
    PositiveOrZeroFloat,
    PositiveOrZeroInt,
)

# Transitional 0.x re-exports, outside __all__: each family block replaces its own (B4-B9).

# -----------------------------
# ---------- Strings ----------
# -----------------------------

from pyvalueobjects._legacy.strings.string import String
from pyvalueobjects._legacy.strings.nullable_string import NullableString
from pyvalueobjects._legacy.strings.non_empty_string import NonEmptyString
from pyvalueobjects._legacy.strings.nullable_non_empty_string import NullableNonEmptyString
from pyvalueobjects._legacy.strings.uuid4 import Uuid4
from pyvalueobjects._legacy.strings.nullable_uuid4 import NullableUuid4

# -----------------------------
# ---------- Time -------------
# -----------------------------

from pyvalueobjects._legacy.dates.isodate import IsoDate

# -----------------------------
# ------ Data Structures ------
# -----------------------------

from pyvalueobjects._legacy.lists.array_list import ArrayList
from pyvalueobjects._legacy.lists.nullable_array_list import NullableArrayList

# -----------------------------
# -------- Security -----------
# -----------------------------

from pyvalueobjects._legacy.security.cve import Cve
from pyvalueobjects._legacy.security.nullable_cve import NullableCve
from pyvalueobjects._legacy.security.cpe import Cpe
from pyvalueobjects._legacy.security.nullable_cpe import NullableCpe

__all__ = [
    "DECIMAL_CONTEXT",
    "Bounded",
    "Bounds",
    "CurrencyMismatchError",
    "DecimalNumber",
    "Float",
    "Int",
    "InvalidFormatError",
    "InvalidTypeError",
    "NegativeDecimal",
    "NegativeFloat",
    "NegativeInt",
    "NegativeOrZeroDecimal",
    "NegativeOrZeroFloat",
    "NegativeOrZeroInt",
    "Numeric",
    "OutOfRangeError",
    "Percentage",
    "PositiveDecimal",
    "PositiveFloat",
    "PositiveInt",
    "PositiveOrZeroDecimal",
    "PositiveOrZeroFloat",
    "PositiveOrZeroInt",
    "PrecisionError",
    "Scalar",
    "Sized",
    "ValueObject",
    "ValueObjectError",
    "ValueObjectMeta",
]
