from bitstring import BitArray


# TODO make this take a BitArray
# TODO flip output order
def variable_length_field(data):
    bits = BitArray(data)
    value = ""

    for i in range(0, len(bits), 8):
        byte = bits[i:i + 8]
        value += byte[1:].bin
        if not byte[0]:
            break

    padding = "0"*_padding(len(value))
    value = padding + value

    return bits[i + 8:], BitArray(bin=value).int


# TODO there must be a better way to do this
def _padding(length):
    if length % 8 != 0:
        floor = length // 8
        return ((floor + 1) * 8) - length
    return 0
