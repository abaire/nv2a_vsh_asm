#!/usr/bin/env python3

import argparse


def main(args):
    return 1


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

        return parser.parse_args()

    exit(main(_parse_args()))
