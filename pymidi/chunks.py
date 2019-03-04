import logging
import sys

from bitstring import BitArray
from pymidi.utils import variable_length_field

log = logging.getLogger(__name__)
log.setLevel("DEBUG")
handler = logging.StreamHandler(stream=sys.stderr)
handler.setFormatter(logging.Formatter(fmt='%(asctime)s %(levelname)s %(message)s',
                                       datefmt='%Y-%m-%d %H:%M:%S'))
log.addHandler(handler)


HEADER_TYPE = b"MThd"
TRACK_TYPE = b"MTrk"

META_EVENT_PREFIX = BitArray("0xFF")
F0_SYSEX_EVENT_PREFIX = BitArray("0xF0")
F7_SYSEX_EVENT_PREFIX = BitArray("0xF7")


def process_chunk(type, length, raw_data):
    log.debug("processing chunk (type: {}, length: {} bytes)...".format(type, length))

    data = BitArray(raw_data)

    if type == HEADER_TYPE:
        header = process_header(data)
        log.info("Header: {}".format(header))

    elif type == TRACK_TYPE:
        track = process_track_chunk(data)
        for evt in track["events"]:
            log.info("Delta: {}, event: {}".format(evt[0], evt[1]))
    else:
        log.warning("Found unknown chunk type {}, skipping...".format(type))


def process_header(data):
    log.info("Parsing header chunk...")
    format = data[:16].int
    # Format 0: a single track
    # Format 1: one or more simultaneous tracks. Normally first Track chunk here is special, and contains
    # all the tempo information in a 'Tempo Map'
    # Format 2: one or more independent tracks
    if format not in [0, 1, 2]:
        log.error("Unrecognised format: {}\n Exiting...".format(format))
        exit(1)

    division = data[-16:]

    if division[0] == 0:
        # bits 0-14 represent number of delta time units in each quarter-note
        division = {
            "format": "time units per quarter note",
            "time_units": division[1:].int
        }
    else:
        # TODO need to test this bit
        # bits 0-7 represent number of delta time units per SMTPE frame
        # bits 8-14 make a negative number, representing number of SMTPE frames per second
        division = {
            "format": "SMTPE",
            "time_units_per_frame": division[-8:].int,
            "frames_per_second": division[1:-8]
        }

    return {
        "format": format,
        "track_count": data[17:32].int,
        "division": division
    }


# TODO wrap Events in a class/structure, and return an array of all the events in the chunk
def process_track_chunk(data):
    log.info("Parsing Track Chunk...")

    # a series of <delta time><event>
    # <delta time> is a variable length field
    events = []
    while len(data) > 0:
        data, delta = variable_length_field(data)
        # where <event> is
        # <sysex event>, first byte is F0 or F7
        # TODO extract these prefixes as constants

        prefix = data[:8]
        if prefix == F0_SYSEX_EVENT_PREFIX or prefix == F7_SYSEX_EVENT_PREFIX:
            log.debug("Sysex event")
            data, event = process_sysex_event(prefix, data[8:])
            events.append((delta, event))
        # <meta event> first byte is FF
        elif prefix == META_EVENT_PREFIX:
            log.debug("Meta event")
            data, event = process_meta_event(data)
            events.append((delta, event))
        # <midi event>
        else:
            log.debug("MIDI event (?)")
            data = process_midi_event(data)
            print('data: ', data)

    return {
        "events": events
    }


def process_meta_event(data):
    # drop the leading FF
    data = data[8:]

    type = data[:8].hex
    remainder, length = variable_length_field(data[8:])

    # TODO split out remainder and event data at the start
    event = {
        "type": "META",
        "sub_type": "Unknown",
        "data": remainder[length * 8:]
    }

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
        event["sub_type"] = "Text Event"
        event["text"] = remainder[:length * 8].bytes

        remainder = remainder[length * 8:]
    elif type == "02":
        event["sub_type"] = "Copyright Notice"
        event["text"] = remainder[:length * 8].bytes

        remainder = remainder[length * 8:]
    elif type == "03":
        event["sub_type"] = "Sequence/Track Name"
        event["text"] = remainder[:length * 8].bytes

        remainder = remainder[length * 8:]
    elif type == "04":
        event["sub_type"] = "Instrument Name"
        event["text"] = remainder[:length * 8].bytes

        remainder = remainder[length * 8:]
    elif type == "05":
        event["sub_type"] = "Lyric"
        event["text"] = remainder[:length * 8].bytes

        remainder = remainder[length * 8:]
    elif type == "06":
        event["sub_type"] = "Marker"
        event["text"] = remainder[:length * 8].bytes

        remainder = remainder[length * 8:]
    elif type == "07":
        event["sub_type"] = "Cue Point"
        event["text"] = remainder[:length * 8].bytes

        remainder = remainder[length * 8:]
    elif type == "20":
        # MIDI Channel Prefix
        # Associate all following meta-events and sysex-events with the specified MIDI channel, until the next
        # <midi_event> (which must contain MIDI channel information).
        if length != 1:
            log.error("Channel Prefix Event has the wrong length!\nExiting...")
            exit(1)

        event["sub_type"] = "MIDI Channel Prefix"
        event["channel"] = remainder[:8].hex

        remainder = remainder[8:]
    elif type == "21":
        # MIDI Prefix Port
        if length != 1:
            print("MIDI Prefix Port event has the wrong length!\nExiting...")
            exit(1)

        event["sub_type"] = "MIDI Prefix Port"
        event["device"] = remainder[:8]

        remainder = remainder[8:]
    elif type == "2f":
        print("End of Track")
        # This event is not optional.
        # It is used to give the track a clearly defined length, which is essential information if the track is looped
        # or concatenated with another track
        # TODO add checks to make sure that this event is present
        if length:
            print("End of Track event should not have any length!\nExiting...")
            exit(1)

        event["sub_type"] = "End of Track"
    elif type == "51":
        # Set Tempo
        # This sets the tempo in microseconds per quarter note. This means a change in the unit-length of a delta-time
        # tick. (note 1)
        # If not specified, the default tempo is 120 beats/minute, which is equivalent to tttttt=500000
        if length != 3:
            print("Set Tempo event has the wrong length!\nExiting...")
            exit(1)

        event["sub_type"] = "Set Tempo"
        event["new_tempo"] = remainder[:8 * 3]

        remainder = remainder[8 * 3:]
    elif type == "54":
        # SMTPE Offset
        # This (optional) event specifies the SMTPE time at which the track is to start.
        # This event must occur before any non-zero delta-times, and before any MIDI events.
        # In a format 1 MIDI file, this event must be on the first track (the tempo map).
        if length != 5:
            print("SMTPE Offset event has the wrong length!\nExiting...")
            exit(1)

        event["sub_type"] = "SMTPE Offset"
        event["hours"] = remainder[:8]
        event["minutes"] = remainder[8:16]
        event["seconds"] = remainder[16:24]
        event["frames"] = remainder[24:32]
        event["fractional_frames"] = remainder[32:40]

        remainder = remainder[40:]
    elif type == "58":
        # Time Signature
        if length != 4:
            print("Time Signature event has the wrong length!\nExiting...")
            exit(1)

        event["sub_type"] = "Time Signature"
        event["numerator"] = remainder[:8]
        event["denominator"] = remainder[8:16]
        # MIDI clocks per metronome click
        event["clocks_per_tick"] = remainder[16:24]
        # number of 1/32 notes per 24 MIDI clocks (8 is standard)
        event["32nd_notes_per_24_clocks"] = remainder[24:32]

        remainder = remainder[32:]
    elif type == "59":
        # Key Signature
        # Key Signature, expressed as the number of sharps or flats, and a major/minor flag.
        # 0 represents a key of C, negative numbers represent 'flats', while positive numbers represent 'sharps'.
        if length != 2:
            print("Key Signature event has the wrong length!\nExiting...")
            exit(1)

        event["sub_type"] = "Key Signature"
        event["sharps_flats"] = remainder[:8].int
        event["major_minor"] = remainder[8:16].int

        remainder = remainder[16:]
    elif type == "7F":
        # This is the MIDI-file equivalent of the System Exclusive Message.
        # A manufacturer may incorporate sequencer-specific directives into a MIDI file using this event.
        # consists of <id> + <data>, length is length of both of these fields combined
        # <id> is either one or three bytes, and is the Manufacturer ID
        # This value is the same as is used for MIDI System Exclusive messages
        # <data> 8-bit binary data

        event["sub_type"] = "Sequencer-Specific Meta-event"
        event["data"] = remainder[:length * 8]

        remainder = remainder[length * 8:]
    else:
        log.warning("Unrecognised Meta event: {}".format(type))
        # skip the data anyway
        remainder = remainder[length * 8:]

    return remainder, event


def process_sysex_event(prefix, data):
    remainder, length = variable_length_field(data)
    if prefix == F0_SYSEX_EVENT_PREFIX:
        subtype = "F0"
    elif prefix == F7_SYSEX_EVENT_PREFIX:
        subtype = "F7"
    else:
        raise Exception("Tried to process Sysex event but invalid prefix {} found.\nExiting...".format(prefix))

    event = {
        "type": "SYSEX",
        "sub_type": subtype,
        "data": remainder[:8 * length]
    }

    return remainder[:8 * length], event


def process_midi_event(data):
    print("MIDI event {}".format(data[:24]))
    channel = data[4:8].hex

    if data[:4] == BitArray("0x8"):
        # Note Off
        print("Note Off, channel {}, note {}, velocity {}".format(channel, data[8:16].hex, data[16:24].hex))
        return data[24:]
    elif data[:4] == BitArray("0x9"):
        # Note On
        print("Note On, channel {}, note {}, velocity {}".format(channel, data[8:16].hex, data[16:24].hex))
        return data[24:]
    elif data[:4] == BitArray("0xA"):
        # Polyphonic Key Pressure
        print("Polyphonic Key Pressure, channel {}, key {}, pressure {}".format(channel, data[8:16].hex,
                                                                                data[16:24].hex))
        return data[24:]
    elif data[:4] == BitArray("0xB"):
        if (data[8:16].hex >= "00") and (data[8:16].hex <= "77"):
            print("Controller Change for channel {} to controller {}, value {}".format(channel, data[8:16].hex,
                                                                                       data[16:24].hex))
            return data[24:]
        elif data[8:12] == BitArray("0x7"):
            return process_channel_mode_message(data[12:], channel)
        else:
            print("Unrecognised message {}\nExiting...".format(data[:24]))
            exit(1)
    elif data[:4] == BitArray("0xC"):
        # Program Change
        print("Program Change, channel {}, new program num {}".format(channel, data[8:16].hex))
        return data[16:]
    elif data[:4] == BitArray("0xD"):
        # Channel Key Pressure
        print("Channel Key Pressure, channel {}, channel pressure {}".format(channel, data[8:16].hex))
        return data[16:]
    elif data[:4] == BitArray("0xE"):
        # Pitch Bend
        print("Pitch Bend, channel {}, lsb {}, msb {}".format(channel, data[8:16], data[16:24].hex))
        return data[24:]
    else:
        print("Unrecognised MIDI event {}.\n Exiting...".format(data[:24]))
        exit(1)


# Already has leading Bn7 trimmed off
# TODO make trimming consistent
def process_channel_mode_message(data, channel):
    if data[:12] == BitArray("0x800"):
        # All Sound Off
        # Turn off all sound, including envelopes of notes still sounding, and reverb-effects (if applicable).
        print("Sound off for channel {}".format(channel))
    elif data[:12] == BitArray("0x900"):
        # Reset All Controllers
        # Reset all controllers to their 'default' positions, including all continuous and switch controllers,
        # pitch-bend, and aftertouch effects.
        # Each controller should be returned to a suitable initial condition for that controller. For example,
        # pitch-bend should be returned to its 'center' position.
        #
        # This message must be ignored if Omni is On (Modes 1 and 2).
        print("Reset all controllers for channel {}".format(channel))
    elif data[:4] == BitArray("0xA"):
        # Local Control
        # Disconnect (or reconnect) the keyboard and the sound generator in a MIDI synthesiser.
        # The keyboard should continue to send messages via the MIDI-out port, and the sound-generation circuitry should
        # continue to respond to message received via the MIDI-in port, regardless of this switch.
        # 00 == disconnect local keyboard from sound generator
        # 7F == reconnect local keyboard to sound generator
        dr = data[4:12]
        # TODO process dr
        print("Local Control for channel {}. Disconnect/reconnect: {}".format(channel, dr))
    elif data[:12] == BitArray("0xB00"):
        # All Notes Off
        # Turn off all notes which for which a note-on MIDI message has been received. (note 1)
        # This only applies to notes turned on via MIDI, and not to notes turned on via pressing keys on a local
        # keyboard.
        #
        # This message must be ignored if Omni is On (Modes 1 and 2).
        #
        # In Mode 4 (as well as Mode 3), this message must only affect the MIDI Channel on which it is received.
        #
        # If a hold-pedal is 'on' (controller 0x40), then this message should not be acted on until the hold-pedal is
        # released.
        print("All Notes Off for channel {}".format(channel))
    elif data[:12] == BitArray("0xC00"):
        # Omni Mode On
        # The receiver should respond only to Channel Voice messages which it receives on it's Basic Channel. (note 2)
        # This puts the receiving MIDI device into Channel Mode 3 or 4, depending on the current state of the Mono/Poly
        # switch. (note 3)
        print("Omni Mode on for channel {}".format(channel))
    elif data[:12] == BitArray("0xD00"):
        # Omni Mode Off
        # The receiver should respond to Channel Voice messages which it receives on any MIDI channel. (note 2)
        # This puts the receiving MIDI device into Channel Mode 1 or 2, depending on the current state of the Mono/Poly
        # switch. (note 3)
        print("Omni Mode off for channel {}".format(channel))
    elif data[:4] == BitArray("0xE"):
        # Mono Mode On
        # Puts the receiver into monophonic mode. (note 2)
        # This puts the receiving MIDI device into Channel Mode 2 or 4, depending on the state of the Omni switch.
        # (note 3)
        #
        # While Omni is on, the m=1 is used.
        #
        # If n+m-1 > Ch.16 there is no wrap-around to Ch.1. Only channels n...16 are used
        # TODO validate this
        m = data[4:12]
        print("Mono Mode on for channel {}, number of MIDI channels to use: {}".format(channel, m))
    elif data[:12] == BitArray("0xF00"):
        # Poly Mode On
        # Puts the receiver into polyphonic mode. (note 2)
        # This puts the receiving MIDI device into Channel Mode 1 or 3, depending on the state of the Omni switch.
        # (note 3)
        print("Poly Mode on for channel {}".format(channel))
    else:
        print("Unrecognised Channel mode message received: B{}7{}".format(channel, data[:12].hex))
        # TODO should this exit if this case is reached?

    return data[12:]
