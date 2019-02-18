import click
from bitstring import BitArray


@click.command()
@click.option("--file", required=True, help="file to parse")
def main(file):
    print("opening file '{}'...".format(file))
    with open(file, "rb") as f:
        file_track_chunks, track_chunks, format = 0, 0, 0
        while True:
            type = f.read(4)
            if not type:
                break

            length = BitArray(f.read(4)).int

            if type == b"MThd":
                format, track_chunks = process_header(f.read(length))
                # Format 0: a single track
                # Format 1: one or more simultaneous tracks. Normally first Track chunk here is special, and contains
                # all the tempo information in a 'Tempo Map'
                # Format 2: one or more independent tracks
                print("Track format: {}".format(format))
            elif type == b"MTrk":
                process_track_chunk(f.read(length), length)
                file_track_chunks += 1
            else:
                print("FOUND UNKNOWN CHUNK, skipping...")
                f.read(length)

    if file_track_chunks != track_chunks:
        print("Number of track chunks in file does not match header info.\nExiting...")
        exit(1)


def process_header(data):
    print("HEADER FOUND")
    bits = BitArray(data)

    format = bits[:16].int
    if format not in [0, 1, 2]:
        print("Unrecognised format: {}\n Exiting...".format(format))
        exit(1)

    track_count = bits[17:32].int
    print("# track chunks: {}".format(track_count))

    division = bits[-16:]

    if division[0] == 0:
        # bits 0-14 represent number of delta time units in each quarter-note
        print("{} delta time units per quarter-note".format(division[1:].int))
    else:
        # TODO need to test this bit
        # bits 0-7 represent number of delta time units per SMTPE frame
        print("{} delta time units per SMTPE frame".format(division[-8:].int))
        # bits 8-14 make a negative number, representing number of SMTPE frames per second
        print("{} SMTPE frames per second".format(division[1:-8]))

    return format, track_count


def process_track_chunk(data, length):
    # TODO does this need length?
    print("\nTRACK CHUNK")
    print("length: {}".format(length))

    # a series of <delta time><event>
    # <delta time> is a variable length field
    while len(data) > 0:
        data, delta = variable_length_field(data)
        print("Delta:", delta)
        # where <event> is
        # <midi event>
        # <sysex event>
        # <meta event>
        if data[:8] == BitArray("0xFF"):
            process_meta_event(data)
        else:
            print("no other identified events, skipping...")
            break


# takes BitArray
# TODO should everything take BitArrays?
def process_meta_event(data):
    # drop the leading FF
    data = data[8:]

    type = data[:8].hex
    remainder, length = variable_length_field(data[8:])
    print("META EVENT, length {}".format(length))
    if type == "00":
        print("Sequence Number")
        # This is an optional event, which must occur only at the start of a track, before any non-zero delta-time.
        #
        # For Format 2 MIDI files, this is used to identify each track.If omitted, the sequences are numbered
        # sequentially in the order the tracks appear.
        #
        # For Format 1 files, this event should occur on the first track only.
    elif type == "01":
        print("Text Event")
    elif type == "02":
        print("Copyright Notice")
    elif type == "03":
        print("Sequence/Track Name")
    elif type == "04":
        print("Instrument Name")
    elif type == "05":
        print("Lyric")
    elif type == "06":
        print("Marker")
    elif type == "07":
        print("Cue Point")
    elif type == "20":
        print("MIDI Channel Prefix")
    elif type == "21":
        print("MIDI Prefix Port")
    elif type == "2F":
        print("End of Track")
    elif type == "51":
        print("Set Tempo")
    elif type == "54":
        print("SMTPE Offset")
    elif type == "58":
        print("Time Signature")
    elif type == "59":
        print("Key Signature")
    elif type == "7F":
        print("Sequencer-Specific Meta-event")
    else:
        print("Unrecognised Meta event")

    data = remainder[:length * 8]

    return remainder[length * 8:]


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

    # handle default case?
    raise Exception("Not a variable length field")


if __name__ == "__main__":
    main()
