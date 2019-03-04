from bitstring import BitArray


# TODO flip output order
def variable_length_field(data):
    """
    Takes a BitArray containing bytes, the beginning of which contain a
    MIDI variable length field. This field is extracted, and returned, along
    with the remainder of the data.

    :param data: an array of bytes containing a variable length field
    :return: the remaining data and the extracted field
    """
    value = ""

    for i in range(0, len(data), 8):
        byte = data[i:i + 8]
        value += byte[1:].bin
        if not byte[0]:
            break

    padding = "0"*_padding(len(value))
    value = padding + value

    return data[i + 8:], BitArray(bin=value).int


# TODO there must be a better way to do this
def _padding(length):
    """
    Figure out how much padding is required to pad 'length' bits
    up to a round number of bytes.

    e.g. 23 would need padding up to 24 (3 bytes) -> returns 1

    :param length: the length of a bit array
    :return: the number of bits needed to pad the array to a round number of bytes
    """
    if length % 8 != 0:
        floor = length // 8
        return ((floor + 1) * 8) - length
    return 0
