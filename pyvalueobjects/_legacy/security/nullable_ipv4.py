from pyvalueobjects._legacy.abstract.nullablevalueobject import build_nullable
from pyvalueobjects._legacy.security.ipv4 import Ipv4

_nullable_cls = build_nullable(Ipv4)


class NullableIpv4(_nullable_cls):
    """
    A nullable value object representing an IPv4 address.
    Inherits from a nullable version of Ipv4 and allows the value to be None.
    """

    def __init__(self, value: str = None):
        """
        Initialize the NullableIpv4 object with the given IPv4 address string value or None.
        :param value: An IPv4 address string value, or None.
        """
        super().__init__(value) 