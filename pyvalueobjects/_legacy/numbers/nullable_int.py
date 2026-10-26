from pyvalueobjects._legacy.abstract.nullablevalueobject import build_nullable
from pyvalueobjects._legacy.numbers.int import Int

_nullable_cls = build_nullable(Int)


class NullableInt(_nullable_cls):
    """
    A nullable value object representing an integer. Inherits from a nullable version of Int and allows the value to be None.
    """

    def __init__(self, value: int = None):
        """
        Initialize the NullableInt object with the given integer value or None.
        :param value: An integer value, or None.
        """
        super().__init__(value)
