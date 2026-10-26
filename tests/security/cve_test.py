import unittest

from pyvalueobjects._legacy.errors.ValueObjectError import ValueObjectError
from pyvalueobjects._legacy.security.cve import Cve


class TestCveValueObject(unittest.TestCase):

    def __init__(self, *args):
        super().__init__(*args)
        self._cls = Cve

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
        vo = Cve('CVE-2023-33000')
        self.assertEqual('CVE-2023-33000', vo.value())

    def test_bad_format_cve_raise_error(self):
        self.assertRaises(ValueObjectError, Cve, 'no-format')

    def test_none_raise_error(self):
        self.assertRaises(ValueObjectError, Cve, None)
