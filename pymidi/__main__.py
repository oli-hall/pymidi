import logging
import sys

import click

from pymidi.chunks import parse_chunks

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


if __name__ == "__main__":
    main()
