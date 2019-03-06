import unittest

from bitstring import BitArray

from pymidi.chunks import parse_chunks, process_header_chunk, process_track_chunk, HEADER, TRACK
from pymidi.events import META_TYPE

FORMAT_0_EXAMPLE = "data/format_0_example_1.mid"
FORMAT_1_EXAMPLE = "data/format_1_example_1.mid"


class ChunksTest(unittest.TestCase):

    def test_parsing_format_0_file_results_in_header_and_track_chunk(self):
        with open(FORMAT_0_EXAMPLE, "rb") as f:
            chunks = parse_chunks(f)

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0]["type"], HEADER)
        self.assertEqual(chunks[1]["type"], TRACK)

    def test_parsing_format_1_file_results_in_header_and_track_chunk(self):
        with open(FORMAT_1_EXAMPLE, "rb") as f:
            chunks = parse_chunks(f)

        self.assertEqual(len(chunks), 5)
        self.assertEqual(chunks[0]["type"], HEADER)
        for chk in chunks[1:]:
            self.assertEqual(chk["type"], TRACK)

    def test_parsing_format_0_file_parses_header_correctly(self):
        with open(FORMAT_0_EXAMPLE, "rb") as f:
            chunks = parse_chunks(f)

        header = chunks[0]

        self.assertEqual(header["type"], HEADER)
        self.assertEqual(header["format"], 0)
        self.assertEqual(header["track_count"], 1)

        division = header["division"]

        self.assertEqual(division["format"], "time units per quarter note")
        self.assertEqual(division["time_units"], 96)

    def test_parsing_format_1_file_parses_header_correctly(self):
        with open(FORMAT_1_EXAMPLE, "rb") as f:
            chunks = parse_chunks(f)

        header = chunks[0]

        self.assertEqual(header["type"], HEADER)
        self.assertEqual(header["format"], 1)
        self.assertEqual(header["track_count"], 4)

        division = header["division"]

        self.assertEqual(division["format"], "time units per quarter note")
        self.assertEqual(division["time_units"], 96)

    def test_parsing_format_1_file_parses_tempo_track_correctly(self):
        with open(FORMAT_1_EXAMPLE, "rb") as f:
            chunks = parse_chunks(f)

        tempo_track = chunks[1]

        self.assertEqual(tempo_track["type"], TRACK)
        self.assertEqual(len(tempo_track["events"]), 3)

        # only testing overall sequence of events, rather than every event field
        events = tempo_track["events"]

        self.assertEqual(events[0][0], 0)
        self.assertEqual(events[0][1]["type"], META_TYPE)
        self.assertEqual(events[0][1]["sub_type"], "Time Signature")

        self.assertEqual(events[1][0], 0)
        self.assertEqual(events[1][1]["type"], META_TYPE)
        self.assertEqual(events[1][1]["sub_type"], "Set Tempo")

        self.assertEqual(events[2][0], 384)
        self.assertEqual(events[2][1]["type"], META_TYPE)
        self.assertEqual(events[2][1]["sub_type"], "End of Track")

    # TODO test that different types of chunk are identified correctly and lengths extracted properly

    def test_header_parsing_parses_header_correctly(self):
        input = BitArray("0x000000010060")

        header = process_header_chunk(6, input)

        self.assertEqual(header["type"], HEADER)
        self.assertEqual(header["format"], 0)
        self.assertEqual(header["track_count"], 1)

        division = header["division"]

        self.assertEqual(division["format"], "time units per quarter note")
        self.assertEqual(division["time_units"], 96)

    def test_header_parsing_raises_exception_if_length_is_not_6(self):
        input = BitArray("0x000000010060")

        self.assertRaises(Exception, process_header_chunk, 5, input)
        self.assertRaises(Exception, process_header_chunk, 7, input)
        self.assertRaises(Exception, process_header_chunk, -1, input)
        self.assertRaises(Exception, process_header_chunk, 9001, input)

    def test_track_parsing_identifies_meta_events_correctly(self):
        input = BitArray("0x00FF58040402180800FF2F00")

        track = process_track_chunk(input)

        self.assertEqual(track["type"], TRACK)
        self.assertEqual(len(track["events"]), 2)

        delta_time = track["events"][0][0]
        event = track["events"][0][1]

        self.assertEqual(delta_time, 0)
        self.assertEqual(event["type"], META_TYPE)
        self.assertEqual(event["sub_type"], "Time Signature")

    def test_track_parsing_raises_exception_if_end_of_track_event_missing(self):
        input = BitArray("0x00FF580404021808")

        self.assertRaises(Exception, process_track_chunk, input)

        input = BitArray("0x00FF2F00")

        track = process_track_chunk(input)

        self.assertEqual(track["type"], TRACK)
        self.assertEqual(len(track["events"]), 1)

        delta_time = track["events"][0][0]
        event = track["events"][0][1]

        self.assertEqual(delta_time, 0)
        self.assertEqual(event["type"], META_TYPE)
        self.assertEqual(event["sub_type"], "End of Track")


if __name__ == "__main__":
    unittest.main()
