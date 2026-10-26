import unittest

from pyvalueobjects.errors.ValueObjectError import ValueObjectError
from pyvalueobjects.numbers.float import Float


class TestFloatValueObject(unittest.TestCase):

    def __init__(self, *args):
        super().__init__(*args)
        self._cls = Float

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
        vo = Float(39.5)
        self.assertEqual(39.5, vo.value())

    def test_value_without_decimals_return_input_value(self):
        vo = Float(39.0)
        self.assertEqual(39.0, vo.value())

    def test_zero_value_return_input_value(self):
        vo = Float(0.0)
        self.assertEqual(0.0, vo.value())

    def test_negative_value_return_input_value(self):
        vo = Float(-39.5)
        self.assertEqual(-39.5, vo.value())

    def test_int_value_raises_error(self):
        self.assertRaises(ValueObjectError, Float, 39)

    def test_bool_value_raises_error(self):
        self.assertRaises(ValueObjectError, Float, True)

    def test_str_value_raises_error(self):
        self.assertRaises(ValueObjectError, Float, '39.5')

    def test_nan_value_raises_error(self):
        self.assertRaises(ValueObjectError, Float, float('nan'))

    def test_infinite_value_raises_error(self):
        self.assertRaises(ValueObjectError, Float, float('inf'))

    def test_negative_infinite_value_raises_error(self):
        self.assertRaises(ValueObjectError, Float, float('-inf'))

    def test_from_int_method_returns_float(self):
        vo = Float.from_int(39)
        self.assertEqual(39.0, vo.value())
        self.assertIs(float, type(vo.value()))

    def test_from_int_method_returns_negative_float(self):
        vo = Float.from_int(-39)
        self.assertEqual(-39.0, vo.value())

    def test_from_int_with_float_raises_error(self):
        self.assertRaises(ValueObjectError, Float.from_int, 39.5)

    def test_from_int_with_bool_raises_error(self):
        self.assertRaises(ValueObjectError, Float.from_int, True)

    def test_from_int_too_large_raises_error(self):
        self.assertRaises(ValueObjectError, Float.from_int, 10 ** 400)

    def test_from_string_method_returns_float(self):
        vo = Float.from_str('39.5')
        self.assertEqual(39.5, vo.value())

    def test_from_string_method_returns_negative_float(self):
        vo = Float.from_str('-39.5')
        self.assertEqual(-39.5, vo.value())

    def test_from_string_without_decimals_returns_float(self):
        vo = Float.from_str('39')
        self.assertEqual(39.0, vo.value())
        self.assertIs(float, type(vo.value()))

    def test_from_string_with_not_numerical_format_raise_error(self):
        self.assertRaises(ValueObjectError, Float.from_str, 'patata')

    def test_from_string_with_non_string_raise_error(self):
        self.assertRaises(ValueObjectError, Float.from_str, 39.5)

    def test_from_string_nan_raise_error(self):
        self.assertRaises(ValueObjectError, Float.from_str, 'nan')

    def test_from_string_infinite_raise_error(self):
        self.assertRaises(ValueObjectError, Float.from_str, 'inf')

    def test_from_string_overflow_raise_error(self):
        self.assertRaises(ValueObjectError, Float.from_str, '1e400')

    def test_none_raise_error(self):
        self.assertRaises(ValueObjectError, Float, None)
