import uuid

from pyvalueobjects._legacy.errors.ValueObjectError import ValueObjectError
from pyvalueobjects._legacy.strings.non_empty_string import NonEmptyString


class Uuid4(NonEmptyString):
    """
    A value object representing a UUID version 4 string. Inherits from NonEmptyString and validates that the input is a valid UUID v4 string.
    """

    def __init__(self, value: str):
        """
        Initialize the Uuid4 object with the given UUID v4 string value.
        :param value: A UUID v4 string value.
        """
        super().__init__(value)

    def _validate(self, value):
        """
        Validate that the given value is a valid UUID v4 string.
        :param value: The value to validate.
        :raises: ValueObjectError if the value is not a valid UUID v4 string.
        """
        super()._validate(value)
        try:
            uuid.UUID(str(value), version=4)
        except ValueError:
            raise ValueObjectError('Value must be valid a uuid4 format strings.')
