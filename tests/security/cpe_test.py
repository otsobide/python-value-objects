import unittest

from pyvalueobjects._legacy.errors.ValueObjectError import ValueObjectError
from pyvalueobjects._legacy.security.cpe import Cpe


class TestCpeIdValueObject(unittest.TestCase):

    def __init__(self, *args):
        super().__init__(*args)
        self._cls = Cpe

    def test_vo_equal_hash(self):
        original_vo_hash = hash(self._cls('cpe:/a:openjdk:openjdk:8u282'))
        equal_vo_hash = hash(self._cls('cpe:/a:openjdk:openjdk:8u282'))
        self.assertEqual(original_vo_hash, equal_vo_hash)

    def test_vo_different_hash(self):
        original_vo_hash = hash(self._cls('cpe:/a:openjdk:openjdk:8u282'))
        not_equal_vo_hash = hash(self._cls('cpe:/o:microsoft:windows_10'))
        self.assertNotEqual(original_vo_hash, not_equal_vo_hash)

    def test_vo_equality(self):
        original_vo = self._cls('cpe:/a:openjdk:openjdk:8u282')
        equal_vo = self._cls('cpe:/a:openjdk:openjdk:8u282')
        self.assertEqual(original_vo, equal_vo)

    def test_vo_different_equality(self):
        original_vo = self._cls('cpe:/a:openjdk:openjdk:8u282')
        different_vo = self._cls('cpe:/o:microsoft:windows_10')
        self.assertNotEqual(original_vo, different_vo)

    def test_value_return_input_value(self):
        vo = Cpe('cpe:/a:openjdk:openjdk:8u282')
        self.assertEqual('cpe:/a:openjdk:openjdk:8u282', vo.value())

    def test_bad_format_cve_raise_error(self):
        self.assertRaises(ValueObjectError, Cpe, 'no-format')

    def test_none_raise_error(self):
        self.assertRaises(ValueObjectError, Cpe, None)
