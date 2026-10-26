from pyvalueobjects._legacy.abstract.nullablevalueobject import build_nullable
from pyvalueobjects._legacy.security.mac_address import MacAddress

_nullable_cls = build_nullable(MacAddress)


class NullableMacAddress(_nullable_cls):
    """
    A nullable value object representing a MAC address.
    Inherits from a nullable version of MacAddress and allows the value to be None.
    """

    def __init__(self, value: str = None):
        """
        Initialize the NullableMacAddress object with the given MAC address string value or None.
        :param value: A MAC address string value, or None.
        """
        super().__init__(value) 