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
    # TODO does this need length? Only here for debugging
    print("\nTRACK CHUNK")
    print("length: {}".format(length))

    # a series of <delta time><event>
    # <delta time> is a variable length field
    while len(data) > 0:
        data, delta = variable_length_field(data)
        print("\nDelta:", delta)
        # where <event> is
        # <midi event>
        # <sysex event>
        # TODO extract these prefixes as constants
        if data[:8] == BitArray("0xF0") or data[:8] == BitArray("0xF7"):
            data = process_sysex_event(data)
        # <meta event>
        elif data[:8] == BitArray("0xFF"):
            data = process_meta_event(data)
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

    # TODO make sure that these comparisons are case correct/case-insensitive
    if type == "00":
        print("Sequence Number")
        # This is an optional event, which must occur only at the start of a track, before any non-zero delta-time.
        #
        # For Format 2 MIDI files, this is used to identify each track.If omitted, the sequences are numbered
        # sequentially in the order the tracks appear.
        #
        # For Format 1 files, this event should occur on the first track only.
    elif type == "01":
        text = remainder[:length * 8]
        remainder = remainder[length * 8:]
        print("Text Event: {}".format(text))
    elif type == "02":
        text = remainder[:length * 8]
        remainder = remainder[length * 8:]
        print("Copyright Notice: {}".format(text))
    elif type == "03":
        text = remainder[:length * 8]
        remainder = remainder[length * 8:]
        print("Sequence/Track Name: {}".format(text))
    elif type == "04":
        text = remainder[:length * 8]
        remainder = remainder[length * 8:]
        print("Instrument Name: {}".format(text))
    elif type == "05":
        text = remainder[:length * 8]
        remainder = remainder[length * 8:]
        print("Lyric: {}".format(text))
    elif type == "06":
        text = remainder[:length * 8]
        remainder = remainder[length * 8:]
        print("Marker: {}".format(text))
    elif type == "07":
        text = remainder[:length * 8]
        remainder = remainder[length * 8:]
        print("Cue Point: {}".format(text))
    elif type == "20":
        # MIDI Channel Prefix
        # Associate all following meta-events and sysex-events with the specified MIDI channel, until the next
        # <midi_event> (which must contain MIDI channel information).
        if length != 1:
            print("This event has the wrong length!\nExiting...")
            exit(1)

        channel = remainder[:8].hex
        remainder = remainder[8:]
        print("MIDI Channel Prefix: channel {}".format(channel))
    elif type == "21":
        # MIDI Prefix Port
        if length != 1:
            print("This event has the wrong length!\nExiting...")
            exit(1)

        device = remainder[:8]
        remainder = remainder[8:]
        print("MIDI Prefix Port: device: {}".format(device))
    elif type == "2f":
        print("End of Track")
        # This event is not optional.
        # It is used to give the track a clearly defined length, which is essential information if the track is looped
        # or concatenated with another track
        # TODO add checks to make sure that this event is present
        if length:
            print("This event should not have any length!\nExiting...")
            exit(1)
    elif type == "51":
        # Set Tempo
        # This sets the tempo in microseconds per quarter note. This means a change in the unit-length of a delta-time
        # tick. (note 1)
        # If not specified, the default tempo is 120 beats/minute, which is equivalent to tttttt=500000
        if length != 3:
            print("This event has the wrong length!\nExiting...")
            exit(1)

        new_tempo = remainder[:8 * 3]
        remainder = remainder[8 * 3:]
        print("Set Tempo: {} μs/quarter-note".format(new_tempo.int))
    elif type == "54":
        # SMTPE Offset
        # This (optional) event specifies the SMTPE time at which the track is to start.
        # This event must occur before any non-zero delta-times, and before any MIDI events.
        # In a format 1 MIDI file, this event must be on the first track (the tempo map).
        if length != 5:
            print("This event has the wrong length!\nExiting...")
            exit(1)

        # TODO expand this and extract sub-fields
        smtpe_offset = remainder[:8 * 5]
        remainder = remainder[8 * 5:]
        print("SMTPE Offset")
    elif type == "58":
        # Time Signature
        if length != 4:
            print("This event has the wrong length!\nExiting...")
            exit(1)

        # TODO expand extraction of sub-elements here
        time_sig = remainder[:8 * 4]
        remainder = remainder[8 * 4:]
        print("Time Signature: {}".format(time_sig))
    elif type == "59":
        # Key Signature
        # Key Signature, expressed as the number of sharps or flats, and a major/minor flag.
        # 0 represents a key of C, negative numbers represent 'flats', while positive numbers represent 'sharps'.
        if length != 2:
            print("This event has the wrong length!\nExiting...")
            exit(1)

        sf = remainder[:8].int
        mi = remainder[8:16].int
        remainder = remainder[16:]
        print("Key Signature. number of sharps/flats: {}, major/minor: {}".format(sf, mi))
    elif type == "7F":
        print("Sequencer-Specific Meta-event")
        # This is the MIDI-file equivalent of the System Exclusive Message.
        # A manufacturer may incorporate sequencer-specific directives into a MIDI file using this event.
        # consists of <id> + <data>, length is length of both of these fields combined
        # <id> is either one or three bytes, and is the Manufacturer ID
        # This value is the same as is used for MIDI System Exclusive messages
        # <data> 8-bit binary data
        remainder = remainder[length * 8:]
    else:
        print("Unrecognised Meta event: {}".format(type))
        # skip the data anyway
        remainder = remainder[length * 8:]

    return remainder


def process_sysex_event(data):
    remainder, length = variable_length_field(data[8:])

    if data[:8] == BitArray("0xF0"):
        print("F0 SYSEX EVENT")
        print("Should send MIDI Message: F0 {}".format(remainder[:8 * length]))
    elif data[:8] == BitArray("0xF7"):
        print("F7 SYSEX EVENT")
        print("Should send MIDI Message: {}".format(remainder[:8 * length]))

    return remainder[:8 * length]


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


if __name__ == "__main__":
    main()
