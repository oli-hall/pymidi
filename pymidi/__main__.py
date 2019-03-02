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
        chunk_type = f.read(4)
        while chunk_type:
            length = BitArray(f.read(4)).int

            process_chunk(chunk_type, length, f.read(length))

            chunk_type = f.read(4)


if __name__ == "__main__":
    main()
