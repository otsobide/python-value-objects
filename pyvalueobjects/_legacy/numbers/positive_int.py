from pyvalueobjects._legacy.errors.ValueObjectError import ValueObjectError
from pyvalueobjects._legacy.numbers.positive_or_zero_int import PositiveOrZeroInt


class PositiveInt(PositiveOrZeroInt):
    """
    A value object representing a positive integer. Inherits from PositiveOrZeroInt and validates that the input is a positive integer.
    """

    def __init__(self, value: int):
        """
        Initialize the PositiveInt object with the given positive integer value.
        :param value: A positive integer value.
        """
        super().__init__(value)

    def _validate(self, value):
        """
        Validate that the given value is a positive integer.
        :param value: The value to validate.
        :raises: ValueObjectError if the value is not a positive integer.
        """
        super()._validate(value)
        if value <= 0:
            raise ValueObjectError('Value must be greater than 0.')
