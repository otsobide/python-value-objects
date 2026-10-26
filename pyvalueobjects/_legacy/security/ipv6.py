import re

from pyvalueobjects._legacy.errors.ValueObjectError import ValueObjectError
from pyvalueobjects._legacy.strings.non_empty_string import NonEmptyString


class Ipv6(NonEmptyString):
    """
    A value object representing an IPv6 address.
    Inherits from NonEmptyString and validates that the input is a valid IPv6 address format.
    IPv6 addresses are 128-bit addresses represented in hexadecimal notation, with eight groups of four hexadecimal digits,
    each group separated by colons (e.g., 2001:0db8:85a3:0000:0000:8a2e:0370:7334).
    """

    __MATCHER = re.compile(r'^(?:(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,7}:|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,5}(?::[0-9a-fA-F]{1,4}){1,2}|(?:[0-9a-fA-F]{1,4}:){1,4}(?::[0-9a-fA-F]{1,4}){1,3}|(?:[0-9a-fA-F]{1,4}:){1,3}(?::[0-9a-fA-F]{1,4}){1,4}|(?:[0-9a-fA-F]{1,4}:){1,2}(?::[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:(?:(?::[0-9a-fA-F]{1,4}){1,6})|:(?:(?::[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(?::[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(?:ffff(?::0{1,4}){0,1}:){0,1}(?:(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])|(?:[0-9a-fA-F]{1,4}:){1,4}:(?:(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9]))$')

    def __init__(self, value: str):
        """
        Initialize the Ipv6 object with the given IPv6 address string value.
        :param value: An IPv6 address string value.
        """
        super().__init__(value)

    def _validate(self, value: str):
        """
        Validate that the given value is a valid IPv6 address format.
        :param value: The value to validate.
        :raises: ValueObjectError if the value is not a valid IPv6 address format.
        """
        super()._validate(value)
        try:
            is_correct = Ipv6.__MATCHER.match(value)
            if not is_correct:
                raise ValueObjectError('Value must be a valid IPv6 address format (e.g. 2001:0db8:85a3:0000:0000:8a2e:0370:7334).')
        except ValueError:
            raise ValueObjectError('Value must be a valid IPv6 address format (e.g. 2001:0db8:85a3:0000:0000:8a2e:0370:7334).') 