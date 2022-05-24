#!/usr/bin/env python3

import argparse
import logging
import os
import sys

import nv2a_vsh_asm


def main(args):
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level)

    if not os.path.isfile(args.input):
        print(f"Failed to open input file '{args.input}'", file=sys.stderr)
        return 1

    with open(args.input, "r") as infile:
        asm = nv2a_vsh_asm.Assembler(infile.read())

    asm.assemble()
    results = asm.get_c_output()

    if args.output:
        with open(args.output, "w") as outfile:
            outfile.write(results)
    else:
        print(results)

    return 0


if __name__ == "__main__":

    def _parse_args():
        parser = argparse.ArgumentParser()

        parser.add_argument(
            "input",
            metavar="source_path",
            help="Source file to assemble.",
        )

        parser.add_argument(
            "output",
            nargs="?",
            metavar="target_path",
            help="Path to write the .inl output.",
        )

        parser.add_argument(
            "-v",
            "--verbose",
            help="Enables verbose logging information",
            action="store_true",
        )

        return parser.parse_args()

    exit(main(_parse_args()))
