from pyvalueobjects._legacy.abstract.nullablevalueobject import build_nullable
from pyvalueobjects._legacy.security.sha256_hash import Sha256Hash

_nullable_cls = build_nullable(Sha256Hash)


class NullableSha256Hash(_nullable_cls):
    """
    A nullable value object representing a SHA-256 hash.
    Inherits from a nullable version of Sha256Hash and allows the value to be None.
    """

    def __init__(self, value: str = None):
        """
        Initialize the NullableSha256Hash object with the given SHA-256 hash string value or None.
        :param value: A SHA-256 hash string value, or None.
        """
        super().__init__(value) 