from pyvalueobjects._legacy.abstract.nullablevalueobject import build_nullable
from pyvalueobjects._legacy.strings.non_empty_string import NonEmptyString

_nullable_cls = build_nullable(NonEmptyString)


class NullableNonEmptyString(_nullable_cls):
    """
    A nullable value object representing a non-empty string. Inherits from a nullable version of NonEmptyString and allows the value to be None.
    """

    def __init__(self, value: str = None):
        """
        Initialize the NullableNonEmptyString object with the given non-empty string value or None.
        :param value: A non-empty string value, or None.
        """
        super().__init__(value)
