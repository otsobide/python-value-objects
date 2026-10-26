import re

from pyvalueobjects._legacy.errors.ValueObjectError import ValueObjectError
from pyvalueobjects._legacy.strings.non_empty_string import NonEmptyString


class Cpe(NonEmptyString):
    """
    A value object representing a Common Platform Enumeration (CPE) string.
    Inherits from NonEmptyString and validates that the input is a valid CPE format string.
    CPE is a standardized way to name and identify classes of applications, operating systems, and hardware devices.
    """

    __MATCHER = re.compile('^cpe:/[aho]:[a-z\d._~-]+:[a-z\d._~-]+(?::[a-z\d._~-]+)?(?::[a-z\d._~-]+)?(?:$|\:['
                           'a-z\d._~-]+)$')

    def __init__(self, value: str):
        """
        Initialize the Cpe object with the given CPE string value.
        :param value: A CPE format string value.
        """
        super().__init__(value)

    def _validate(self, value: str):
        """
        Validate that the given value is a valid CPE format string.
        :param value: The value to validate.
        :raises: ValueObjectError if the value is not a valid CPE format string.
        """
        super()._validate(value)
        try:
            is_correct = Cpe.__MATCHER.match(value)
            if not is_correct:
                raise ValueObjectError('Value must be valid a CPE format strings.')
        except ValueError:
            raise ValueObjectError('Value must be valid a CPE format strings.')
