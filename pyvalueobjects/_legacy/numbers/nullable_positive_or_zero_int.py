from pyvalueobjects._legacy.abstract.nullablevalueobject import build_nullable
from pyvalueobjects._legacy.numbers.positive_or_zero_int import PositiveOrZeroInt

_nullable_cls = build_nullable(PositiveOrZeroInt)


class NullablePositiveOrZeroInt(_nullable_cls):
    """
    A nullable value object representing a positive integer or zero. Inherits from a nullable version of PositiveOrZeroInt and allows the value to be None.
    """

    def __init__(self, value: int = None):
        """
        Initialize the NullablePositiveOrZeroInt object with the given positive integer or zero value or None.
        :param value: A positive integer or zero value, or None.
        """
        super().__init__(value)
