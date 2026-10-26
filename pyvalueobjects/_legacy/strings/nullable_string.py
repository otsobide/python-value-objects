from pyvalueobjects._legacy.abstract.nullablevalueobject import build_nullable
from pyvalueobjects._legacy.strings.string import String

_nullable_cls = build_nullable(String)


class NullableString(_nullable_cls):
    """
    A nullable value object representing a string. Inherits from a nullable version of String and allows the value to be None.
    """

    def __init__(self, value: str = None):
        """
        Initialize the NullableString object with the given string value or None.
        :param value: A string value, or None.
        """
        super().__init__(value)
