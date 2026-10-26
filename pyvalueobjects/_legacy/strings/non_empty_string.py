from pyvalueobjects._legacy.errors.ValueObjectError import ValueObjectError
from pyvalueobjects._legacy.strings.string import String


class NonEmptyString(String):
    """
    A value object representing a non-empty string. Inherits from String and validates that the input is a non-empty string.
    """

    def __init__(self, value: str):
        """
        Initialize the NonEmptyString object with the given non-empty string value.
        :param value: A non-empty string value.
        """
        super().__init__(value)

    def _validate(self, value):
        """
        Validate that the given value is a non-empty string.
        :param value: The value to validate.
        :raises: ValueObjectError if the value is an empty string.
        """
        super()._validate(value)
        if value == '':
            raise ValueObjectError('Value must be a non empty strings.')
