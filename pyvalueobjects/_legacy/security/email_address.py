import re

from pyvalueobjects._legacy.errors.ValueObjectError import ValueObjectError
from pyvalueobjects._legacy.strings.non_empty_string import NonEmptyString


class EmailAddress(NonEmptyString):
    """
    A value object representing an email address.
    Inherits from NonEmptyString and validates that the input is a valid email address format.
    The email address must follow the standard format: local-part@domain
    """

    __MATCHER = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

    def __init__(self, value: str):
        """
        Initialize the EmailAddress object with the given email address string value.
        :param value: An email address string value.
        """
        super().__init__(value)

    def _validate(self, value: str):
        """
        Validate that the given value is a valid email address format.
        :param value: The value to validate.
        :raises: ValueObjectError if the value is not a valid email address format.
        """
        super()._validate(value)
        try:
            is_correct = EmailAddress.__MATCHER.match(value)
            if not is_correct:
                raise ValueObjectError('Value must be a valid email address format (e.g. user@example.com).')
        except ValueError:
            raise ValueObjectError('Value must be a valid email address format (e.g. user@example.com).') 