from pyvalueobjects._legacy.abstract.nullablevalueobject import build_nullable
from pyvalueobjects._legacy.security.ipv6 import Ipv6

_nullable_cls = build_nullable(Ipv6)


class NullableIpv6(_nullable_cls):
    """
    A nullable value object representing an IPv6 address.
    Inherits from a nullable version of Ipv6 and allows the value to be None.
    """

    def __init__(self, value: str = None):
        """
        Initialize the NullableIpv6 object with the given IPv6 address string value or None.
        :param value: An IPv6 address string value, or None.
        """
        super().__init__(value) 