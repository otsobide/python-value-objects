import math

from pyvalueobjects._legacy.abstract.valueobject import ValueObject
from pyvalueobjects._legacy.errors.ValueObjectError import ValueObjectError


class Float(ValueObject):
    """
    A value object representing a float. Inherits from ValueObject and validates that the input is a finite float.
    """

    def __init__(self, value: float):
        """
        Initialize the Float object with the given float value.
        :param value: A float value.
        """
        super().__init__(value)

    @classmethod
    def from_int(cls, value: int):
        """
        Create a Float object from an int value.
        :param value: An int value.
        :return: A Float object.
        :raises: ValueObjectError if the value is not an int or cannot be represented as a float.
        """
        if type(value) != int:
            raise ValueObjectError('Input type should be int.')

        try:
            float_value = float(value)
        except OverflowError:
            raise ValueObjectError('Input value is too large to be a float.')

        return cls(float_value)

    @classmethod
    def from_str(cls, value: str):
        """
        Create a Float object from a string value. The string must represent a valid number.
        :param value: A string representing a number.
        :return: A Float object.
        :raises: ValueObjectError if the value is not a valid number string.
        """
        if type(value) != str:
            raise ValueObjectError('Input type should be str.')

        try:
            float_value = float(value)
        except ValueError:
            raise ValueObjectError('Input type should be number format strings.')

        return cls(float_value)

    def _validate(self, value):
        """
        Validate that the given value is a finite float.
        :param value: The value to validate.
        :raises: ValueObjectError if the value is not a float, or is NaN or infinite.
        """
        super()._validate(value)
        input_type = type(value)
        if input_type != float:
            raise ValueObjectError('Input type should be: float.')
        if not math.isfinite(value):
            raise ValueObjectError('Value must be a finite number.')
