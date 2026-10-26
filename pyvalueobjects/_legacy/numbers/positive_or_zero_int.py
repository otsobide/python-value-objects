from pyvalueobjects._legacy.errors.ValueObjectError import ValueObjectError
from pyvalueobjects._legacy.numbers.int import Int


class PositiveOrZeroInt(Int):
    """
    A value object representing a positive integer or zero. Inherits from Int and validates that the input is a positive integer or zero.
    """

    def __init__(self, value: int):
        """
        Initialize the PositiveOrZeroInt object with the given positive integer or zero value.
        :param value: A positive integer or zero value.
        """
        super().__init__(value)

    def _validate(self, value):
        """
        Validate that the given value is a positive integer or zero.
        :param value: The value to validate.
        :raises: ValueObjectError if the value is not a positive integer or zero.
        """
        super()._validate(value)
        if value < 0:
            raise ValueObjectError('Value must be greater or equals to 0.')
