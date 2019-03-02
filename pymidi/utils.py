from bitstring import BitArray


def variable_length_field(data):
    # return any spare data?
    bits = BitArray(data)

    extracted = BitArray(bin="00")

    for i in range(0, len(bits), 8):
        byte = bits[i:i + 8]
        if byte[0]:
            extracted.append(byte[1:])
        else:
            extracted.append(byte[1:])
            return bits[i + 8:], extracted.int

    # TODO improve edge-case handling
    raise Exception("Not a variable length field")
