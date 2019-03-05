import logging
import sys

import click
from bitstring import BitArray

from pymidi.chunks import process_chunk

log = logging.getLogger(__name__)
log.setLevel('INFO')
handler = logging.StreamHandler(stream=sys.stderr)
handler.setFormatter(logging.Formatter(fmt='%(asctime)s %(levelname)s %(message)s',
                                       datefmt='%Y-%m-%d %H:%M:%S'))
log.addHandler(handler)


@click.command()
@click.option("--file", required=True, help="file to parse")
def main(file):
    log.debug("opening file '{}'...".format(file))
    with open(file, "rb") as f:
        chunks = parse_chunks(f)
        # basic track printing routine
        print("\n")
        for chunk in chunks:
            if not chunk:
                print("Missing/Unparseable chunk. Skipping...\n")
                continue
            type_ = chunk["type"]
            print("{} chunk".format(type_))
            if type_ == "header":
                for k, v in chunk.items():
                    if k != "type":
                        print(k, v)
            else:
                for evt in chunk["events"]:
                    print("Delta: {}".format(evt[0]))
                    for k, v in evt[1].items():
                        print(k, v)
                    print("")
            print("")


def parse_chunks(f):
    chunks = []
    chunk_type = f.read(4)
    while chunk_type:
        length = BitArray(f.read(4)).int

        chunks.append(process_chunk(chunk_type, length, f.read(length)))

        chunk_type = f.read(4)

    return chunks


if __name__ == "__main__":
    main()
