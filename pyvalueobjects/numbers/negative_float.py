from pyvalueobjects.errors.ValueObjectError import ValueObjectError
from pyvalueobjects.numbers.float import Float


class NegativeFloat(Float):
    """
    A value object representing a negative float. Inherits from Float and validates that the input is a negative float.
    """

    def __init__(self, value: float):
        """
        Initialize the NegativeFloat object with the given negative float value.
        :param value: A negative float value.
        """
        super().__init__(value)

    def _validate(self, value):
        """
        Validate that the given value is a negative float.
        :param value: The value to validate.
        :raises: ValueObjectError if the value is not a negative float.
        """
        super()._validate(value)
        if value >= 0:
            raise ValueObjectError('Value must be less than 0.')
