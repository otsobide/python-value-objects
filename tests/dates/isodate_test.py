import datetime
import unittest

from pyvalueobjects._legacy.dates.isodate import IsoDate
from pyvalueobjects._legacy.errors.ValueObjectError import ValueObjectError


class TestIsoDateValueObject(unittest.TestCase):

    def __init__(self, *args):
        super().__init__(*args)
        self._cls = IsoDate

    def test_vo_equal_hash(self):
        the_date = datetime.datetime.now().isoformat()
        original_vo_hash = hash(self._cls(the_date))
        equal_vo_hash = hash(self._cls(the_date))
        self.assertEqual(original_vo_hash, equal_vo_hash)

    def test_vo_different_hash(self):
        the_date = datetime.datetime.now().isoformat()
        one_day_ago = (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat()
        original_vo_hash = hash(self._cls(the_date))
        not_equal_vo_hash = hash(self._cls(one_day_ago))
        self.assertNotEqual(original_vo_hash, not_equal_vo_hash)

    def test_vo_equality(self):
        the_date = datetime.datetime.now().isoformat()
        original_vo = self._cls(the_date)
        equal_vo = self._cls(the_date)
        self.assertEqual(original_vo, equal_vo)

    def test_vo_different_equiality(self):
        the_date = datetime.datetime.now().isoformat()
        one_day_ago = (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat()
        original_vo = self._cls(the_date)
        not_equal_vo = self._cls(one_day_ago)
        self.assertNotEqual(original_vo, not_equal_vo)

    def test_value_return_input_value(self):
        the_date = datetime.datetime.now().isoformat()
        vo = IsoDate(the_date)
        self.assertEqual(the_date, vo.value())

    def test_none_raise_error(self):
        self.assertRaises(ValueObjectError, IsoDate, None)

    def test_ctime_format_raise_error(self):
        self.assertRaises(ValueObjectError, IsoDate, datetime.datetime.now().ctime())

    def test_empty_string_raise_error(self):
        self.assertRaises(ValueObjectError, IsoDate, '')

    def test_random_string_raise_error(self):
        self.assertRaises(ValueObjectError, IsoDate, 'patata')
