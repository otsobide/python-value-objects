from pyvalueobjects._legacy.abstract.nullablevalueobject import build_nullable
from pyvalueobjects._legacy.security.url import Url

_nullable_cls = build_nullable(Url)


class NullableUrl(_nullable_cls):
    """
    A nullable value object representing a URL (Uniform Resource Locator).
    Inherits from a nullable version of Url and allows the value to be None.
    """

    def __init__(self, value: str = None):
        """
        Initialize the NullableUrl object with the given URL string value or None.
        :param value: A URL string value, or None.
        """
        super().__init__(value) 