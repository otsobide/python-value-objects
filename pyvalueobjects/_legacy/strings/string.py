from pyvalueobjects._legacy.abstract.valueobject import ValueObject
from pyvalueobjects._legacy.errors.ValueObjectError import ValueObjectError


class String(ValueObject):
    """
    A value object representing a string. Inherits from ValueObject and validates that the input is a string.
    """

    _ALLOWED_INPUT_TYPES = {str, int, float, bool}

    def __init__(self, value: str):
        """
        Initialize the String object with the given string value.
        :param value: A string value.
        """
        super().__init__(value)

    def _validate(self, value):
        """
        Validate that the given value is a string.
        :param value: The value to validate.
        :raises: ValueObjectError if the value is not a string.
        """
        super()._validate(value)
        input_type = type(value)
        if input_type != str:
            raise ValueObjectError(f'Input type should be: str.')
