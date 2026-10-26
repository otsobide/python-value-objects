from pyvalueobjects._legacy.abstract.nullablevalueobject import build_nullable
from pyvalueobjects._legacy.numbers.negative_or_zero_int import NegativeOrZeroInt

_nullable_cls = build_nullable(NegativeOrZeroInt)


class NullableNegativeOrZeroInt(_nullable_cls):
    """
    A nullable value object representing a negative integer or zero. Inherits from a nullable version of NegativeOrZeroInt and allows the value to be None.
    """

    def __init__(self, value: int = None):
        """
        Initialize the NullableNegativeOrZeroInt object with the given negative integer or zero value or None.
        :param value: A negative integer or zero value, or None.
        """
        super().__init__(value)
