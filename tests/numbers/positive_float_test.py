import unittest

from pyvalueobjects._legacy.errors.ValueObjectError import ValueObjectError
from pyvalueobjects._legacy.numbers.positive_float import PositiveFloat


class TestPositiveFloatValueObject(unittest.TestCase):

    def __init__(self, *args):
        super().__init__(*args)
        self._cls = PositiveFloat

    def test_vo_equal_hash(self):
        original_vo_hash = hash(self._cls(39.5))
        equal_vo_hash = hash(self._cls(39.5))
        self.assertEqual(original_vo_hash, equal_vo_hash)

    def test_vo_different_hash(self):
        original_vo_hash = hash(self._cls(39.5))
        not_equal_vo_hash = hash(self._cls(97.5))
        self.assertNotEqual(original_vo_hash, not_equal_vo_hash)

    def test_vo_equality(self):
        original_vo = self._cls(39.5)
        equal_vo = self._cls(39.5)
        self.assertEqual(original_vo, equal_vo)

    def test_vo_different_equality(self):
        original_vo = self._cls(39.5)
        different_vo = self._cls(97.5)
        self.assertNotEqual(original_vo, different_vo)

    def test_value_return_input_value(self):
        vo = PositiveFloat(39.5)
        self.assertEqual(39.5, vo.value())

    def test_small_value_return_input_value(self):
        vo = PositiveFloat(0.001)
        self.assertEqual(0.001, vo.value())

    def test_from_int_method_returns_float(self):
        vo = PositiveFloat.from_int(39)
        self.assertEqual(39.0, vo.value())

    def test_from_string_method_returns_float(self):
        vo = PositiveFloat.from_str('39.5')
        self.assertEqual(39.5, vo.value())

    def test_zero_value_raises_error(self):
        self.assertRaises(ValueObjectError, PositiveFloat, 0.0)

    def test_negative_zero_value_raises_error(self):
        self.assertRaises(ValueObjectError, PositiveFloat, -0.0)

    def test_zero_from_int_method_raises_error(self):
        self.assertRaises(ValueObjectError, PositiveFloat.from_int, 0)

    def test_zero_from_string_method_raises_error(self):
        self.assertRaises(ValueObjectError, PositiveFloat.from_str, '0')

    def test_negative_value_raises_error(self):
        self.assertRaises(ValueObjectError, PositiveFloat, -39.5)

    def test_negative_from_int_method_raises_error(self):
        self.assertRaises(ValueObjectError, PositiveFloat.from_int, -39)

    def test_negative_from_string_method_raises_error(self):
        self.assertRaises(ValueObjectError, PositiveFloat.from_str, '-39.5')

    def test_infinite_value_raises_error(self):
        self.assertRaises(ValueObjectError, PositiveFloat, float('inf'))

    def test_int_value_raises_error(self):
        self.assertRaises(ValueObjectError, PositiveFloat, 39)

    def test_none_raise_error(self):
        self.assertRaises(ValueObjectError, PositiveFloat, None)
