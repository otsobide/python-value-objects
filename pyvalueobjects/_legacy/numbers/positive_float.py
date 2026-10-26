from pyvalueobjects._legacy.errors.ValueObjectError import ValueObjectError
from pyvalueobjects._legacy.numbers.float import Float


class PositiveFloat(Float):
    """
    A value object representing a positive float. Inherits from Float and validates that the input is a positive float.
    """

    def __init__(self, value: float):
        """
        Initialize the PositiveFloat object with the given positive float value.
        :param value: A positive float value.
        """
        super().__init__(value)

    def _validate(self, value):
        """
        Validate that the given value is a positive float.
        :param value: The value to validate.
        :raises: ValueObjectError if the value is not a positive float.
        """
        super()._validate(value)
        if value <= 0:
            raise ValueObjectError('Value must be greater than 0.')
