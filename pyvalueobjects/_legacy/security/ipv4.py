import re

from pyvalueobjects._legacy.errors.ValueObjectError import ValueObjectError
from pyvalueobjects._legacy.strings.non_empty_string import NonEmptyString


class Ipv4(NonEmptyString):
    """
    A value object representing an IPv4 address.
    Inherits from NonEmptyString and validates that the input is a valid IPv4 address format.
    IPv4 addresses consist of four octets separated by dots (e.g., 192.168.1.1).
    """

    __MATCHER = re.compile(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')

    def __init__(self, value: str):
        """
        Initialize the Ipv4 object with the given IPv4 address string value.
        :param value: An IPv4 address string value.
        """
        super().__init__(value)

    def _validate(self, value: str):
        """
        Validate that the given value is a valid IPv4 address format.
        :param value: The value to validate.
        :raises: ValueObjectError if the value is not a valid IPv4 address format.
        """
        super()._validate(value)
        try:
            is_correct = Ipv4.__MATCHER.match(value)
            if not is_correct:
                raise ValueObjectError('Value must be a valid IPv4 address format (e.g. 192.168.1.1).')
        except ValueError:
            raise ValueObjectError('Value must be a valid IPv4 address format (e.g. 192.168.1.1).') 