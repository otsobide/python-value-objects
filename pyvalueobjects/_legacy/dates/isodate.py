import datetime

from pyvalueobjects._legacy.errors.ValueObjectError import ValueObjectError
from pyvalueobjects._legacy.strings.string import String


class IsoDate(String):
    """
    A value object representing a date in ISO format. Inherits from String and validates that the input is a valid ISO date string.
    """

    def __init__(self, value: str):
        """
        Initialize the IsoDate object with the given ISO date string.
        :param value: A string representing a date in ISO format.
        """
        super().__init__(value)

    def _validate(self, value):
        """
        Validate that the given value is a valid ISO date string.
        :param value: The string to validate.
        :raises: ValueObjectError if the value is not a valid ISO date string.
        """
        super()._validate(value)
        try:
            datetime.datetime.fromisoformat(value)
        except ValueError:
            raise ValueObjectError('Value must be valid a iso date format strings.')
