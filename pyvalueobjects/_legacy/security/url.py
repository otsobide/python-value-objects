import re

from pyvalueobjects._legacy.errors.ValueObjectError import ValueObjectError
from pyvalueobjects._legacy.strings.non_empty_string import NonEmptyString


class Url(NonEmptyString):
    """
    A value object representing a URL (Uniform Resource Locator).
    Inherits from NonEmptyString and validates that the input is a valid URL format.
    Supports HTTP and HTTPS URLs, including domains, IP addresses, localhost, and optional ports.
    """

    __MATCHER = re.compile(
        r'^(?:http[s]?://)?'  # http:// or https:// (optional)
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    def __init__(self, value: str):
        """
        Initialize the Url object with the given URL string value.
        :param value: A URL string value.
        """
        super().__init__(value)

    def _validate(self, value: str):
        """
        Validate that the given value is a valid URL format.
        :param value: The value to validate.
        :raises: ValueObjectError if the value is not a valid URL format.
        """
        super()._validate(value)
        try:
            is_correct = Url.__MATCHER.match(value)
            if not is_correct:
                raise ValueObjectError('Value must be a valid URL format (e.g. https://example.com or http://localhost:8080).')
        except ValueError:
            raise ValueObjectError('Value must be a valid URL format (e.g. https://example.com or http://localhost:8080).') 