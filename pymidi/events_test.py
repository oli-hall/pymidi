import unittest

from bitstring import BitArray
from pymidi.events import process_meta_event, META_TYPE


class EventsTest(unittest.TestCase):

    # TODO rest of the META events
    # TODO test parsing them with trailing data
    def test_parsing_meta_events(self):
        input = BitArray("0x580404021808")

        remainder, event = process_meta_event(input)

        self.assertEqual(remainder, BitArray())
        self.assertEqual(event["type"], META_TYPE)
        self.assertEqual(event["sub_type"], "Time Signature")
        self.assertEqual(event["numerator"], 4)
        self.assertEqual(event["denominator"], 2)
        self.assertEqual(event["clocks_per_tick"], 24)
        self.assertEqual(event["32nd_notes_per_24_clocks"], 8)

    # TODO test parsing of sysex events


if __name__ == "__main__":
    unittest.main()
