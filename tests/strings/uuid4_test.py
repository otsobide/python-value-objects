import unittest
import uuid

from pyvalueobjects._legacy.errors.ValueObjectError import ValueObjectError
from pyvalueobjects._legacy.strings.uuid4 import Uuid4


class TestUuid4ValueObject(unittest.TestCase):

    def __init__(self, *args):
        super().__init__(*args)
        self._cls = Uuid4

    def test_vo_equal_hash(self):
        original_vo_hash = hash(self._cls('e88cf76c-904b-4f4f-81ee-8524a60bf5d0'))
        equal_vo_hash = hash(self._cls('e88cf76c-904b-4f4f-81ee-8524a60bf5d0'))
        self.assertEqual(original_vo_hash, equal_vo_hash)

    def test_vo_different_hash(self):
        original_vo_hash = hash(self._cls('e88cf76c-904b-4f4f-81ee-8524a60bf5d0'))
        not_equal_vo_hash = hash(self._cls('c8ab500c-bd40-4bb2-8feb-efb22404f404'))
        self.assertNotEqual(original_vo_hash, not_equal_vo_hash)

    def test_vo_equality(self):
        original_vo = self._cls('e88cf76c-904b-4f4f-81ee-8524a60bf5d0')
        equal_vo = self._cls('e88cf76c-904b-4f4f-81ee-8524a60bf5d0')
        self.assertEqual(original_vo, equal_vo)

    def test_vo_different_equality(self):
        original_vo = self._cls('e88cf76c-904b-4f4f-81ee-8524a60bf5d0')
        different_vo = self._cls('c8ab500c-bd40-4bb2-8feb-efb22404f404')
        self.assertNotEqual(original_vo, different_vo)

    def test_value_return_input_value(self):
        the_uuid = str(uuid.uuid4())
        vo = Uuid4(the_uuid)
        self.assertEqual(the_uuid, vo.value())

    def test_none_raise_error(self):
        self.assertRaises(ValueObjectError, Uuid4, None)

    def test_empty_string_raise_error(self):
        self.assertRaises(ValueObjectError, Uuid4, '')

    def test_random_string_raise_error(self):
        self.assertRaises(ValueObjectError, Uuid4, 'patata')

    def test_old_uuid_version_raise_error(self):
        self.assertRaises(ValueObjectError, Uuid4, uuid.uuid1())
