import re

from pyvalueobjects._legacy.errors.ValueObjectError import ValueObjectError
from pyvalueobjects._legacy.strings.non_empty_string import NonEmptyString


class Md5Hash(NonEmptyString):
    """
    A value object representing an MD5 hash.
    Inherits from NonEmptyString and validates that the input is a valid MD5 hash format.
    MD5 hashes are 128-bit (16-byte) hashes represented as 32 hexadecimal characters.
    """

    __MATCHER = re.compile(r'^[a-fA-F0-9]{32}$')

    def __init__(self, value: str):
        """
        Initialize the Md5Hash object with the given MD5 hash string value.
        :param value: An MD5 hash string value.
        """
        super().__init__(value)

    def _validate(self, value: str):
        """
        Validate that the given value is a valid MD5 hash format.
        :param value: The value to validate.
        :raises: ValueObjectError if the value is not a valid MD5 hash format.
        """
        super()._validate(value)
        try:
            is_correct = Md5Hash.__MATCHER.match(value)
            if not is_correct:
                raise ValueObjectError('Value must be a valid MD5 hash (32 hexadecimal characters).')
        except ValueError:
            raise ValueObjectError('Value must be a valid MD5 hash (32 hexadecimal characters).') 