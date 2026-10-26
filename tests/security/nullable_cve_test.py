import unittest

from pyvalueobjects._legacy.errors.ValueObjectError import ValueObjectError
from pyvalueobjects._legacy.security.nullable_cve import NullableCve


class TestNullableCveValueObject(unittest.TestCase):

    def __init__(self, *args):
        super().__init__(*args)
        self._cls = NullableCve

    def test_vo_equal_hash(self):
        original_vo_hash = hash(self._cls('CVE-2023-33000'))
        equal_vo_hash = hash(self._cls('CVE-2023-33000'))
        self.assertEqual(original_vo_hash, equal_vo_hash)

    def test_vo_different_hash(self):
        original_vo_hash = hash(self._cls('CVE-2023-33000'))
        not_equal_vo_hash = hash(self._cls('CVE-2021-34527'))
        self.assertNotEqual(original_vo_hash, not_equal_vo_hash)

    def test_vo_equality(self):
        original_vo = self._cls('CVE-2023-33000')
        equal_vo = self._cls('CVE-2023-33000')
        self.assertEqual(original_vo, equal_vo)

    def test_vo_different_equality(self):
        original_vo = self._cls('CVE-2023-33000')
        different_vo = self._cls('CVE-2021-34527')
        self.assertNotEqual(original_vo, different_vo)

    def test_value_return_input_value(self):
        self.assertRaises(ValueObjectError, NullableCve, '')

    def test_basic_cve(self):
        vo = NullableCve('CVE-2023-33000')
        self.assertEqual('CVE-2023-33000', vo.value())

    def test_none_return_none(self):
        vo = NullableCve(None)
        self.assertEqual(None, vo.value())

