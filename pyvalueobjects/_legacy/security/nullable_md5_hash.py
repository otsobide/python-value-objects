from pyvalueobjects._legacy.abstract.nullablevalueobject import build_nullable
from pyvalueobjects._legacy.security.md5_hash import Md5Hash

_nullable_cls = build_nullable(Md5Hash)


class NullableMd5Hash(_nullable_cls):
    """
    A nullable value object representing an MD5 hash.
    Inherits from a nullable version of Md5Hash and allows the value to be None.
    """

    def __init__(self, value: str = None):
        """
        Initialize the NullableMd5Hash object with the given MD5 hash string value or None.
        :param value: An MD5 hash string value, or None.
        """
        super().__init__(value) 