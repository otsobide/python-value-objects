from pyvalueobjects._legacy.errors.ValueObjectError import ValueObjectError
from pyvalueobjects._legacy.numbers.negative_or_zero_int import NegativeOrZeroInt


class NegativeInt(NegativeOrZeroInt):
    """
    A value object representing a negative integer. Inherits from NegativeOrZeroInt and validates that the input is a negative integer.
    """

    def __init__(self, value: int):
        """
        Initialize the NegativeInt object with the given negative integer value.
        :param value: A negative integer value.
        """
        super().__init__(value)

    def _validate(self, value):
        """
        Validate that the given value is a negative integer.
        :param value: The value to validate.
        :raises: ValueObjectError if the value is not a negative integer.
        """
        super()._validate(value)
        if value >= 0:
            raise ValueObjectError('Value must be less than 0.')
