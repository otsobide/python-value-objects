from pyvalueobjects._legacy.numbers.positive_int import PositiveInt
from pyvalueobjects._legacy.abstract.nullablevalueobject import build_nullable

_nullable_cls = build_nullable(PositiveInt)


class NullablePositiveInt(_nullable_cls):
    """
    A nullable value object representing a positive integer. Inherits from a nullable version of PositiveInt and allows the value to be None.
    """

    def __init__(self, value: int = None):
        """
        Initialize the NullablePositiveInt object with the given positive integer value or None.
        :param value: A positive integer value, or None.
        """
        super().__init__(value)
