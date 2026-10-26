import re

from pyvalueobjects._legacy.errors.ValueObjectError import ValueObjectError
from pyvalueobjects._legacy.strings.non_empty_string import NonEmptyString


class MacAddress(NonEmptyString):
    """
    A value object representing a MAC (Media Access Control) address.
    Inherits from NonEmptyString and validates that the input is a valid MAC address format.
    MAC addresses are 48-bit addresses represented in hexadecimal notation, with six groups of two hexadecimal digits,
    each group separated by colons or hyphens (e.g., 00:1A:2B:3C:4D:5E or 00-1A-2B-3C-4D-5E).
    """

    __MATCHER = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')

    def __init__(self, value: str):
        """
        Initialize the MacAddress object with the given MAC address string value.
        :param value: A MAC address string value.
        """
        super().__init__(value)

    def _validate(self, value: str):
        """
        Validate that the given value is a valid MAC address format.
        :param value: The value to validate.
        :raises: ValueObjectError if the value is not a valid MAC address format.
        """
        super()._validate(value)
        try:
            is_correct = MacAddress.__MATCHER.match(value)
            if not is_correct:
                raise ValueObjectError('Value must be a valid MAC address format (e.g. 00:1A:2B:3C:4D:5E or 00-1A-2B-3C-4D-5E).')
        except ValueError:
            raise ValueObjectError('Value must be a valid MAC address format (e.g. 00:1A:2B:3C:4D:5E or 00-1A-2B-3C-4D-5E).') 