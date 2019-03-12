import logging
import sys

from bitstring import BitArray

from pymidi.events import process_meta_event, process_sysex_event, process_midi_event, F0_SYSEX_EVENT_PREFIX, \
    F7_SYSEX_EVENT_PREFIX, META_EVENT_PREFIX
from pymidi.utils import variable_length_field

log = logging.getLogger(__name__)
log.setLevel("INFO")
handler = logging.StreamHandler(stream=sys.stderr)
handler.setFormatter(logging.Formatter(fmt="%(asctime)s %(levelname)s %(message)s",
                                       datefmt="%Y-%m-%d %H:%M:%S"))
log.addHandler(handler)


HEADER_TYPE = b"MThd"
TRACK_TYPE = b"MTrk"
HEADER = "header"
TRACK = "track"


def parse_chunks(f):
    chunks = []
    chunk_type = f.read(4)
    while chunk_type:
        length = BitArray(f.read(4)).int

        chunks.append(process_chunk(chunk_type, length, f.read(length)))

        chunk_type = f.read(4)

    return chunks


def process_chunk(type, length, raw_data):
    data = BitArray(raw_data)

    if type == HEADER_TYPE:
        return process_header_chunk(length, data)

    elif type == TRACK_TYPE:
        try:
            return process_track_chunk(data)
        except Exception as e:
            log.error("Error processing Track chunk: {}".format(e))
            return None
    else:
        log.warning("Found unknown chunk type {}, skipping...".format(type))
        return None


def process_header_chunk(length, data):
    log.info("Parsing header chunk...")
    if length != 6:
        raise Exception("Expected 6 byte length for Header chunk, found {} bytes.".format(length))
    format_ = data[:16].int
    # Format 0: a single track
    # Format 1: one or more simultaneous tracks. Normally first Track chunk here is special, and contains
    # all the tempo information in a 'Tempo Map'
    # Format 2: one or more independent tracks
    if format_ not in [0, 1, 2]:
        log.error("Unrecognised format: {}\n Exiting...".format(format_))
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
        "type": HEADER,
        "format": format_,
        "track_count": data[16:32].int,
        "division": division
    }


def process_track_chunk(data):
    log.info("Parsing Track Chunk...")

    events = []
    running_status = None
    while len(data) > 0:
        data, delta = variable_length_field(data)
        prefix = data[:8]
        if prefix == F0_SYSEX_EVENT_PREFIX or prefix == F7_SYSEX_EVENT_PREFIX:
            data, event = process_sysex_event(prefix, data[8:])
            events.append((delta, event))
        elif prefix == META_EVENT_PREFIX:
            data, event = process_meta_event(data[8:])
            events.append((delta, event))
        else:
            data, event, running_status = process_midi_event(data, running_status)
            events.append((delta, event))

    if events[-1][1]["sub_type"] != "End of Track":
        raise Exception("End of Track event missing")

    return {
        "type": TRACK,
        "events": events
    }
