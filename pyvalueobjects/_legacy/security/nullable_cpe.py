from pyvalueobjects._legacy.abstract.nullablevalueobject import build_nullable
from pyvalueobjects._legacy.security.cpe import Cpe

_nullable_cls = build_nullable(Cpe)


class NullableCpe(_nullable_cls):
    """
    A nullable value object representing a Common Platform Enumeration (CPE) string.
    Inherits from a nullable version of Cpe and allows the value to be None.
    """

    def __init__(self, value: str = None):
        """
        Initialize the NullableCpe object with the given CPE string value or None.
        :param value: A CPE format string value, or None.
        """
        super().__init__(value)
