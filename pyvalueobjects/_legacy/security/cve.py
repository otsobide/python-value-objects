import re

from pyvalueobjects._legacy.errors.ValueObjectError import ValueObjectError
from pyvalueobjects._legacy.strings.non_empty_string import NonEmptyString


class Cve(NonEmptyString):
    """
    A value object representing a Common Vulnerabilities and Exposures (CVE) identifier.
    Inherits from NonEmptyString and validates that the input is a valid CVE ID format string.
    CVE IDs follow the format CVE-YYYY-NNNN, where YYYY is the year and NNNN is a unique identifier.
    """

    __MATCHER = re.compile(r'^CVE-\d{4}-\d{4,}$')

    def __init__(self, value: str):
        """
        Initialize the Cve object with the given CVE ID string value.
        :param value: A CVE ID format string value.
        """
        super().__init__(value)

    def _validate(self, value: str):
        """
        Validate that the given value is a valid CVE ID format string.
        :param value: The value to validate.
        :raises: ValueObjectError if the value is not a valid CVE ID format string.
        """
        super()._validate(value)
        try:
            is_correct = Cve.__MATCHER.match(value)
            if not is_correct:
                raise ValueObjectError('Value must be valid a CVE id format strings.')
        except ValueError:
            raise ValueObjectError('Value must be valid a CVE id format strings.')

