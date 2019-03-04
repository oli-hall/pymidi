import unittest

from bitstring import BitArray

from pymidi.utils import variable_length_field


class MidiTest(unittest.TestCase):

    def test_variable_length_decoding_of_0_returns_correct_result(self):
        input = "0x00"

        remainder, extracted = variable_length_field(input)

        self.assertEqual(extracted, 0)
        self.assertEqual(remainder, BitArray())

    def test_variable_length_decoding_of_127_returns_correct_result(self):
        input = "0x7F"

        remainder, extracted = variable_length_field(input)

        self.assertEqual(extracted, 127)
        self.assertEqual(remainder, BitArray())

    def test_variable_length_decoding_of_128_returns_correct_result(self):
        input = "0x8100"

        remainder, extracted = variable_length_field(input)

        self.assertEqual(extracted, 128)
        self.assertEqual(remainder, BitArray())

    def test_variable_length_decoding_of_1000_returns_correct_result(self):
        input = "0x8768"

        remainder, extracted = variable_length_field(input)

        self.assertEqual(extracted, 1000)
        self.assertEqual(remainder, BitArray())

    def test_variable_length_decoding_of_16383_returns_correct_result(self):
        input = "0xFF7F"

        remainder, extracted = variable_length_field(input)

        self.assertEqual(extracted, 16383)
        self.assertEqual(remainder, BitArray())

    def test_variable_length_decoding_of_1000000_returns_correct_result(self):
        input = "0xBD8440"

        remainder, extracted = variable_length_field(input)

        self.assertEqual(extracted, 1000000)
        self.assertEqual(remainder, BitArray())

    def test_variable_length_decoding_of_268435455_returns_correct_result(self):
        input = "0xFFFFFF7F"

        remainder, extracted = variable_length_field(input)

        self.assertEqual(extracted, 268435455)
        self.assertEqual(remainder, BitArray())

    def test_variable_length_decoding_of_268435455_with_excess_data_returns_correct_result_and_correct_remainder(self):
        input = "0xFFFFFF7F12304FABC"

        remainder, extracted = variable_length_field(input)

        self.assertEqual(extracted, 268435455)
        self.assertEqual(remainder, BitArray("0x12304FABC"))


if __name__ == "__main__":
    unittest.main()
