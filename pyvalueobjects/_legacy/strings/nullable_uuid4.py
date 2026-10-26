from pyvalueobjects._legacy.abstract.nullablevalueobject import build_nullable
from pyvalueobjects._legacy.strings.uuid4 import Uuid4

_nullable_cls = build_nullable(Uuid4)


class NullableUuid4(_nullable_cls):
    """
    A nullable value object representing a UUID version 4 string. Inherits from a nullable version of Uuid4 and allows the value to be None.
    """

    def __init__(self, value: str = None):
        """
        Initialize the NullableUuid4 object with the given UUID v4 string value or None.
        :param value: A UUID v4 string value, or None.
        """
        super().__init__(value)
