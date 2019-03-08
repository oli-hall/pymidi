import unittest

from bitstring import BitArray
from pymidi.events import process_meta_event, META, process_midi_event, MIDI


class EventsTest(unittest.TestCase):

    # TODO rest of the META events
    # TODO test parsing them with trailing data
    def test_parsing_meta_events(self):
        input = BitArray("0x580404021808")

        remainder, event = process_meta_event(input)

        self.assertEqual(remainder, BitArray())
        self.assertEqual(event["type"], META)
        self.assertEqual(event["sub_type"], "Time Signature")
        self.assertEqual(event["numerator"], 4)
        self.assertEqual(event["denominator"], 2)
        self.assertEqual(event["clocks_per_tick"], 24)
        self.assertEqual(event["32nd_notes_per_24_clocks"], 8)

    # TODO test parsing of sysex events

    def test_parsing_midi_event(self):
        input = BitArray("0x923060")

        remainder, event, running_status = process_midi_event(input)

        self.assertEqual(remainder, BitArray())
        self.assertEqual(event["type"], MIDI)
        self.assertEqual(event["sub_type"], "Note On")
        self.assertEqual(event["channel"], 3)
        self.assertEqual(event["note"], 48)
        self.assertEqual(event["velocity"], 96)

        self.assertEqual(running_status, (9, 3))

    def test_parsing_midi_event_with_running_status(self):
        input = BitArray("0x3C60")

        status = (9, 3)
        remainder, event, running_status = process_midi_event(input, status)

        self.assertEqual(remainder, BitArray())
        self.assertEqual(event["type"], MIDI)
        self.assertEqual(event["sub_type"], "Note On")
        self.assertEqual(event["channel"], 3)
        self.assertEqual(event["note"], 60)
        self.assertEqual(event["velocity"], 96)

        self.assertEqual(running_status, status)

    def test_parsing_midi_event_without_status_without_running_status_raises_exception(self):
        input = BitArray("0x3C60")

        self.assertRaises(Exception, process_midi_event, input)


if __name__ == "__main__":
    unittest.main()
