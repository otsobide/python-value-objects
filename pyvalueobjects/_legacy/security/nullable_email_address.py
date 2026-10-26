from pyvalueobjects._legacy.abstract.nullablevalueobject import build_nullable
from pyvalueobjects._legacy.security.email_address import EmailAddress

_nullable_cls = build_nullable(EmailAddress)


class NullableEmailAddress(_nullable_cls):
    """
    A nullable value object representing an email address.
    Inherits from a nullable version of EmailAddress and allows the value to be None.
    """

    def __init__(self, value: str = None):
        """
        Initialize the NullableEmailAddress object with the given email address string value or None.
        :param value: An email address string value, or None.
        """
        super().__init__(value) 