import re

from pyvalueobjects._legacy.errors.ValueObjectError import ValueObjectError
from pyvalueobjects._legacy.strings.non_empty_string import NonEmptyString


class Sha256Hash(NonEmptyString):
    """
    A value object representing a SHA-256 hash.
    Inherits from NonEmptyString and validates that the input is a valid SHA-256 hash format.
    SHA-256 hashes are 256-bit (32-byte) hashes represented as 64 hexadecimal characters.
    """

    __MATCHER = re.compile(r'^[a-fA-F0-9]{64}$')

    def __init__(self, value: str):
        """
        Initialize the Sha256Hash object with the given SHA-256 hash string value.
        :param value: A SHA-256 hash string value.
        """
        super().__init__(value)

    def _validate(self, value: str):
        """
        Validate that the given value is a valid SHA-256 hash format.
        :param value: The value to validate.
        :raises: ValueObjectError if the value is not a valid SHA-256 hash format.
        """
        super()._validate(value)
        try:
            is_correct = Sha256Hash.__MATCHER.match(value)
            if not is_correct:
                raise ValueObjectError('Value must be a valid SHA256 hash (64 hexadecimal characters).')
        except ValueError:
            raise ValueObjectError('Value must be a valid SHA256 hash (64 hexadecimal characters).') 