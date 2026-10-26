from pyvalueobjects._legacy.abstract.nullablevalueobject import build_nullable
from pyvalueobjects._legacy.security.cve import Cve

_nullable_cls = build_nullable(Cve)


class NullableCve(_nullable_cls):
    """
    A nullable value object representing a Common Vulnerabilities and Exposures (CVE) identifier.
    Inherits from a nullable version of Cve and allows the value to be None.
    """

    def __init__(self, value: str = None):
        """
        Initialize the NullableCve object with the given CVE ID string value or None.
        :param value: A CVE ID format string value, or None.
        """
        super().__init__(value)
