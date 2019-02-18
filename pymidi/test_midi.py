import unittest

from bitstring import BitArray

from pymidi.__main__ import variable_length_field


class MidiTest(unittest.TestCase):

    def test_variable_length_decoding(self):
        input = "0xFF7F"

        remainder, extracted = variable_length_field(input)

        self.assertEqual(extracted, 16383)
        self.assertEqual(remainder, BitArray())


if __name__ == "__main__":
    unittest.main()
