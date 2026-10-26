import unittest

from pyvalueobjects.lists.array_list import ArrayList
from pyvalueobjects.lists.nullable_array_list import NullableArrayList
from pyvalueobjects.numbers.int import Int
from pyvalueobjects.strings.string import String


class TestNullableArrayListValueObject(unittest.TestCase):
    def test_value_return_input_value(self):
        vo = NullableArrayList(Int)([39])
        self.assertEqual([39], vo.value())

    def test_empty_list_value_return_input_value(self):
        vo = NullableArrayList(Int)([])
        self.assertEqual([], vo.value())

    def test_negative_value_return_input_value(self):
        vo = NullableArrayList(String)(['a', 'b'])
        self.assertEqual(['a', 'b'], vo.value())

    def test_none_value_return_none(self):
        vo = NullableArrayList(String)(None)
        self.assertEqual(None, vo.value())

    def test_same_element_type_returns_same_class(self):
        self.assertIs(NullableArrayList(Int), NullableArrayList(Int))

    def test_different_element_type_returns_different_class(self):
        self.assertIsNot(NullableArrayList(Int), NullableArrayList(String))

    def test_vo_is_instance_of_its_class(self):
        vo = NullableArrayList(Int)([39])
        self.assertIsInstance(vo, NullableArrayList(Int))

    def test_none_vo_is_instance_of_its_class(self):
        vo = NullableArrayList(Int)(None)
        self.assertIsInstance(vo, NullableArrayList(Int))

    def test_vo_is_not_instance_of_other_element_type_class(self):
        vo = NullableArrayList(Int)([39])
        self.assertNotIsInstance(vo, NullableArrayList(String))

    def test_vo_is_instance_of_array_list_class(self):
        vo = NullableArrayList(Int)([39])
        self.assertIsInstance(vo, ArrayList(Int))

    def test_vos_with_same_element_type_have_same_type(self):
        vo = NullableArrayList(Int)([39])
        other_vo = NullableArrayList(Int)(None)
        self.assertIs(type(vo), type(other_vo))
