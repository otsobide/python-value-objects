from pyvalueobjects._legacy.numbers.negative_int import NegativeInt
from pyvalueobjects._legacy.abstract.nullablevalueobject import build_nullable

_nullable_cls = build_nullable(NegativeInt)


class NullableNegativeInt(_nullable_cls):
    """
    A nullable value object representing a negative integer. Inherits from a nullable version of NegativeInt and allows the value to be None.
    """

    def __init__(self, value: int = None):
        """
        Initialize the NullableNegativeInt object with the given negative integer value or None.
        :param value: A negative integer value, or None.
        """
        super().__init__(value)
