from pyvalueobjects._legacy.abstract.valueobject import ValueObject
from pyvalueobjects._legacy.errors.ValueObjectError import ValueObjectError


class Int(ValueObject):
    """
    A value object representing an integer. Inherits from ValueObject and validates that the input is an integer.
    """

    _ALLOWED_INPUT_TYPES = {str, int, float}

    def __init__(self, value: int):
        """
        Initialize the Int object with the given integer value.
        :param value: An integer value.
        """
        super().__init__(value)

    @classmethod
    def from_float(cls, value: float):
        """
        Create an Int object from a float value. The float must be an integer (no decimals).
        :param value: A float value.
        :return: An Int object.
        :raises: ValueObjectError if the value is not a float or has decimals.
        """
        if type(value) != float:
            raise ValueObjectError('Input type should be float.')

        if not value.is_integer():
            raise ValueObjectError('Input type should be float without decimals.')

        try:
            return cls(int(value))
        except Exception as _:
            raise ValueObjectError('Input type should be valid float.')

    @classmethod
    def from_str(cls, value: str):
        """
        Create an Int object from a string value. The string must represent a valid integer.
        :param value: A string representing an integer.
        :return: An Int object.
        :raises: ValueObjectError if the value is not a valid integer string.
        """
        try:
            decimal_value = float(value)

            if not decimal_value.is_integer():
                raise ValueObjectError('Input type shouldnot have decimals.')

            int_value = int(decimal_value)

            return cls(int_value)
        except Exception as _:
            raise ValueObjectError('Input type should be number format strings.')

    def _validate(self, value):
        """
        Validate that the given value is an integer.
        :param value: The value to validate.
        :raises: ValueObjectError if the value is not an integer.
        """
        super()._validate(value)
        input_type = type(value)
        if input_type != int:
            raise ValueObjectError(f'Input type should be: int.')
