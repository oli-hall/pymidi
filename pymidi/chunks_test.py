import unittest
from pymidi.chunks import parse_chunks

FORMAT_0_EXAMPLE = "data/format_0_example_1.mid"
FORMAT_1_EXAMPLE = "data/format_1_example_1.mid"


class ChunksTest(unittest.TestCase):

    def test_parsing_format_0_file_results_in_header_and_track_chunk(self):
        with open(FORMAT_0_EXAMPLE, "rb") as f:
            chunks = parse_chunks(f)

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0]["type"], "header")
        self.assertEqual(chunks[1]["type"], "track")

    def test_parsing_format_1_file_results_in_header_and_track_chunk(self):
        with open(FORMAT_1_EXAMPLE, "rb") as f:
            chunks = parse_chunks(f)

        self.assertEqual(len(chunks), 5)
        self.assertEqual(chunks[0]["type"], "header")
        for chk in chunks[1:]:
            self.assertEqual(chk["type"], "track")

    def test_parsing_format_0_file_parses_header_correctly(self):
        with open(FORMAT_0_EXAMPLE, "rb") as f:
            chunks = parse_chunks(f)

        self.assertEqual(len(chunks), 2)

        header = chunks[0]

        self.assertEqual(header["type"], "header")
        self.assertEqual(header["format"], 0)
        self.assertEqual(header["track_count"], 1)

        division = header["division"]

        self.assertEqual(division["format"], "time units per quarter note")
        self.assertEqual(division["time_units"], 96)

    def test_parsing_format_1_file_parses_header_correctly(self):
        with open(FORMAT_1_EXAMPLE, "rb") as f:
            chunks = parse_chunks(f)

        self.assertEqual(len(chunks), 5)

        header = chunks[0]

        self.assertEqual(header["type"], "header")
        self.assertEqual(header["format"], 1)
        self.assertEqual(header["track_count"], 4)

        division = header["division"]

        self.assertEqual(division["format"], "time units per quarter note")
        self.assertEqual(division["time_units"], 96)
