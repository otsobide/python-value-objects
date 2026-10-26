from pyvalueobjects._legacy.errors.ValueObjectError import ValueObjectError
from pyvalueobjects._legacy.numbers.int import Int


class NegativeOrZeroInt(Int):
    """
    A value object representing a negative integer or zero. Inherits from Int and validates that the input is a negative integer or zero.
    """

    def __init__(self, value: int):
        """
        Initialize the NegativeOrZeroInt object with the given negative integer or zero value.
        :param value: A negative integer or zero value.
        """
        super().__init__(value)

    def _validate(self, value):
        """
        Validate that the given value is a negative integer or zero.
        :param value: The value to validate.
        :raises: ValueObjectError if the value is not a negative integer or zero.
        """
        super()._validate(value)
        if value > 0:
            raise ValueObjectError('Value must be less or equals to 0.')
