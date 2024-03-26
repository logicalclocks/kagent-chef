import unittest

from kagent_utils import IntervalParser
from kagent_utils import UnrecognizedIntervalException

class TestIntervalParser(unittest.TestCase):
    
    @classmethod
    def setUpClass(self):
        self.parser = IntervalParser()

    def test_with_empty_interval(self):
        with self.assertRaises(UnrecognizedIntervalException) as ex:
            self.parser.get_interval_in_ms('')
        self.assertEqual("Could not parse interal value: ", ex.exception.message)
            
    def test_with_unknown_time_unit(self):
        with self.assertRaises(UnrecognizedIntervalException) as ex:
            self.parser.get_interval_in_ms('5g')
        self.assertEqual("Unknown time unit: g", ex.exception.message)
        
    def test_with_default_time_unit(self):
        in_ms = self.parser.get_interval_in_ms('5')
        self.assertEqual(5000, in_ms)

    def test_with_time_unit(self):
        in_ms = self.parser.get_interval_in_ms('5ms')
        self.assertEqual(5, in_ms)

        in_ms = self.parser.get_interval_in_ms('5s')
        self.assertEqual(5000, in_ms)

        in_ms = self.parser.get_interval_in_ms('5m')
        self.assertEqual(300000, in_ms)

        in_ms = self.parser.get_interval_in_ms('5h')
        self.assertEqual(18000000, in_ms)

        in_ms = self.parser.get_interval_in_ms('5d')
        self.assertEqual(432000000, in_ms)

    def test_get_interval_in_seconds(self):
        in_s = self.parser.get_interval_in_s('5m')
        self.assertEqual(300, in_s)
