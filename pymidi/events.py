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


F0_SYSEX_EVENT_PREFIX = BitArray("0xF0")
F7_SYSEX_EVENT_PREFIX = BitArray("0xF7")
META_EVENT_PREFIX = BitArray("0xFF")
META = "META"
MIDI = "MIDI"


def process_meta_event(data):
    type = data[:8].hex
    data, length = variable_length_field(data[8:])

    event_data = data[:length * 8]
    remainder = data[length * 8:]

    event = {
        "type": META,
        "sub_type": "Unknown",
        "data": event_data
    }

    # TODO make sure that these comparisons are case correct/case-insensitive
    if type == "00":
        # This is an optional event, which must occur only at the start of a track, before any non-zero delta-time.
        #
        # For Format 2 MIDI files, this is used to identify each track.If omitted, the sequences are numbered
        # sequentially in the order the tracks appear.
        #
        # For Format 1 files, this event should occur on the first track only.
        event["sub_type"] = "Sequence Number"
        event["sequence_number"] = event_data[:length * 8].bytes
    elif type == "01":
        event["sub_type"] = "Text Event"
        event["text"] = event_data[:length * 8].bytes
    elif type == "02":
        event["sub_type"] = "Copyright Notice"
        event["text"] = event_data[:length * 8].bytes
    elif type == "03":
        event["sub_type"] = "Sequence/Track Name"
        event["text"] = event_data[:length * 8].bytes
    elif type == "04":
        event["sub_type"] = "Instrument Name"
        event["text"] = event_data[:length * 8].bytes
    elif type == "05":
        event["sub_type"] = "Lyric"
        event["text"] = event_data[:length * 8].bytes
    elif type == "06":
        event["sub_type"] = "Marker"
        event["text"] = event_data[:length * 8].bytes
    elif type == "07":
        event["sub_type"] = "Cue Point"
        event["text"] = event_data[:length * 8].bytes
    elif type == "20":
        # MIDI Channel Prefix
        # Associate all following meta-events and sysex-events with the specified MIDI channel, until the next
        # <midi_event> (which must contain MIDI channel information).
        if length != 1:
            log.error("Channel Prefix Event has the wrong length!\nExiting...")
            exit(1)

        event["sub_type"] = "MIDI Channel Prefix"
        event["channel"] = event_data[:8].hex
    elif type == "21":
        # MIDI Prefix Port
        if length != 1:
            print("MIDI Prefix Port event has the wrong length!\nExiting...")
            exit(1)

        event["sub_type"] = "MIDI Prefix Port"
        event["device"] = event_data[:8]
    elif type == "2f":
        print("End of Track")
        # This event is not optional.
        # It is used to give the track a clearly defined length, which is essential information if the track is looped
        # or concatenated with another track
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
        event["new_tempo"] = event_data[:8 * 3]
    elif type == "54":
        # SMTPE Offset
        # This (optional) event specifies the SMTPE time at which the track is to start.
        # This event must occur before any non-zero delta-times, and before any MIDI events.
        # In a format 1 MIDI file, this event must be on the first track (the tempo map).
        if length != 5:
            print("SMTPE Offset event has the wrong length!\nExiting...")
            exit(1)

        event["sub_type"] = "SMTPE Offset"
        event["hours"] = event_data[:8]
        event["minutes"] = event_data[8:16]
        event["seconds"] = event_data[16:24]
        event["frames"] = event_data[24:32]
        event["fractional_frames"] = event_data[32:40]
    elif type == "58":
        # Time Signature
        if length != 4:
            print("Time Signature event has the wrong length!\nExiting...")
            exit(1)

        event["sub_type"] = "Time Signature"
        event["numerator"] = event_data[:8].int
        event["denominator"] = event_data[8:16].int
        # MIDI clocks per metronome click
        event["clocks_per_tick"] = event_data[16:24].int
        # number of 1/32 notes per 24 MIDI clocks (8 is standard)
        event["32nd_notes_per_24_clocks"] = event_data[24:32].int
    elif type == "59":
        # Key Signature
        # Key Signature, expressed as the number of sharps or flats, and a major/minor flag.
        # 0 represents a key of C, negative numbers represent 'flats', while positive numbers represent 'sharps'.
        if length != 2:
            print("Key Signature event has the wrong length!\nExiting...")
            exit(1)

        event["sub_type"] = "Key Signature"
        event["sharps_flats"] = event_data[:8].int
        event["major_minor"] = event_data[8:16].int
    elif type == "7F":
        # This is the MIDI-file equivalent of the System Exclusive Message.
        # A manufacturer may incorporate sequencer-specific directives into a MIDI file using this event.
        # consists of <id> + <data>, length is length of both of these fields combined
        # <id> is either one or three bytes, and is the Manufacturer ID
        # This value is the same as is used for MIDI System Exclusive messages
        # <data> 8-bit binary data

        event["sub_type"] = "Sequencer-Specific Meta-event"
        event["data"] = event_data[:length * 8]
    else:
        log.warning("Unrecognised Meta event: {}".format(type))

    return remainder, event


# TODO translate F0 sysex messages into corresponding MIDI messages
# F0 <length> <bytes>
# becomes
# MIDI message F0 <bytes>
#
# bytes should end with F7 to mark the end of the sysex message
# However, multi-packet Sysex messages can be marked as continuations of
# previous messages by beginning them with F7
#
# e.g.
# F0 03 43 12 00
# 81 48                 200-tick delta time
# F7 06 43 12 00 43 12 00
# 64                    100-tick delta time
# F7 04 43 12 00 F7
#
# Here, a multi-packet message starts  with F0, and continues through
# several delta-time increments, so each continuation begins with F7,
# and the last one ends with F7
def process_sysex_event(prefix, data):
    data, length = variable_length_field(data)
    if prefix == F0_SYSEX_EVENT_PREFIX:
        subtype = "F0"
    elif prefix == F7_SYSEX_EVENT_PREFIX:
        subtype = "F7"
    else:
        raise Exception("Tried to process Sysex event but invalid prefix {} found.\nExiting...".format(prefix))

    event = {
        "type": "SYSEX",
        "sub_type": subtype,
        "data": data[:8 * length]
    }

    return data[:8 * length], event


# TODO add in cancels for running status
# if the Running Status has been cancelled, subsequent data-bytes are ignored until a new status-byte is received
# TODO tidy up this method - it's a mess
def process_midi_event(data, running_status=None):
    # all MIDI message status bytes (I think):
    # 8, 9, A, B, C, D, E

    if is_status_byte(data[:4].uint):
        status = data[:4].uint
        # Channels are identified from 0 -> F, but are referred to as 1 - 16
        channel = data[4:8].uint + 1
        data = data[8:]
    else:
        if running_status is not None:
            status = running_status[0]
            channel = running_status[1]
        else:
            raise Exception("No status byte, and no running status set")

    if status == 8:
        event = {
            "type": MIDI,
            "sub_type": "Note Off",
            "channel": channel,
            "note": data[:8].uint,
            "velocity": data[8:16].uint
        }
        return data[16:], event, (status, channel)
    elif status == 9:
        velocity = data[8:16].uint
        if velocity == 0:
            # note-on with velocity=0 == note-off with velocity=48
            event = {
                "type": MIDI,
                "sub_type": "Note Off",
                "channel": channel,
                "note": data[:8].uint,
                "velocity": 48
            }
            # TODO does this affect running status potentially?
            return data[16:], event, (8, channel)
        else:
            event = {
                "type": MIDI,
                "sub_type": "Note On",
                "channel": channel,
                "note": data[:8].uint,
                "velocity": velocity
            }
            return data[16:], event, (status, channel)
    elif status == 10:
        # Polyphonic Key Pressure
        event = {
            "type": MIDI,
            "sub_type": "Polyphonic Key Pressure",
            "channel": channel,
            "key": data[:8].uint,
            "pressure": data[8:16].uint
        }
        return data[16:], event, (status, channel)
    elif status == 11:
        if (data[:8].hex >= "00") and (data[:8].hex <= "77"):
            event = {
                "type": MIDI,
                "sub_type": "Controller Change",
                "channel": channel,
                "new_controller": data[:8].int,
                "value": data[8:16].int
            }
            return data[16:], event, (status, channel)
        elif data[:4] == BitArray("0x7"):
            return process_channel_mode_message(data[4:], channel)
        else:
            print("Unrecognised message {}\nExiting...".format(data[:16]))
            exit(1)
    elif status == 12:
        event = {
            "type": MIDI,
            "sub_type": "Program Change",
            "channel": channel,
            "new_value": data[:8].int
        }
        return data[8:], event, (status, channel)
    elif status == 13:
        event = {
            "type": MIDI,
            "sub_type": "Channel Key Pressure",
            "channel": channel,
            "channel_pressure": data[:8].uint
        }
        return data[8:], event, (status, channel)
    elif status == 14:
        event = {
            "type": MIDI,
            "sub_type": "Pitch Bend",
            "channel": channel,
            "lsb": data[:8],
            "msb": data[8:16]
        }
        return data[16:], event, (status, channel)
    else:
        raise Exception("Unrecognised MIDI event {}".format(data[:16]))


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


def is_status_byte(byte):
    return 8 <= byte <= 14
