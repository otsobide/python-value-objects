import unittest

from pyvalueobjects._legacy.errors.ValueObjectError import ValueObjectError
from pyvalueobjects._legacy.lists.array_list import ArrayList
from pyvalueobjects._legacy.numbers.int import Int
from pyvalueobjects._legacy.strings.string import String


class TestArrayListValueObject(unittest.TestCase):
    def test_value_return_input_value(self):
        vo = ArrayList(Int)([39])
        self.assertEqual([39], vo.value())

    def test_value_return_input_string_value(self):
        vo = ArrayList(String)(['a'])
        self.assertEqual(['a'], vo.value())

    def test_value_return_empty_array(self):
        vo = ArrayList(Int)([])
        self.assertEqual([], vo.value())

    def test_value_return_empty_string_array(self):
        vo = ArrayList(String)([])
        self.assertEqual([], vo.value())

    def test_value_return_multiple_input_values(self):
        vo = ArrayList(Int)([39, 100])
        self.assertEqual([39, 100], vo.value())

    def test_value_return_input_multiple_string_values(self):
        vo = ArrayList(String)(['a', 'b'])
        self.assertEqual(['a', 'b'], vo.value())

    def test_same_element_type_returns_same_class(self):
        self.assertIs(ArrayList(Int), ArrayList(Int))

    def test_different_element_type_returns_different_class(self):
        self.assertIsNot(ArrayList(Int), ArrayList(String))

    def test_vo_is_instance_of_its_class(self):
        vo = ArrayList(Int)([39])
        self.assertIsInstance(vo, ArrayList(Int))

    def test_vo_is_not_instance_of_other_element_type_class(self):
        vo = ArrayList(Int)([39])
        self.assertNotIsInstance(vo, ArrayList(String))

    def test_vos_with_same_element_type_have_same_type(self):
        vo = ArrayList(Int)([39])
        other_vo = ArrayList(Int)([97])
        self.assertIs(type(vo), type(other_vo))

    def test_invalid_element_raises_error(self):
        self.assertRaises(ValueObjectError, ArrayList(Int), ['a'])

    def test_none_raises_error(self):
        self.assertRaises(ValueObjectError, ArrayList(Int), None)