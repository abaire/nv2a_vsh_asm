#!/usr/bin/env python3

"""Disassembles nv2a vertex shader machine code."""

import argparse
import logging
import os
import re
import sys
from typing import List

from .nv2a_vsh_asm import vsh_instruction

_HEX_MATCH = r"0x[0-9a-fA-F]+"
_VALUE_RE = re.compile(r"\s*(" + _HEX_MATCH + r")\s*,?", re.MULTILINE)


def _parse_text_input(infile):
    content = infile.read()

    values = []
    for match in re.finditer(_VALUE_RE, content):
        values.append(int(match.group(1), 16))

    num_values = len(values)
    if (num_values % 4) != 0:
        raise Exception(f"Invalid input, {num_values} is not divisible by 4.")

    values = [values[start : start + 4] for start in range(0, num_values, 4)]
    return values


def _parse_binary_input(infile):
    raise Exception("TODO: Implement me.")


def disassemble(values: List[List[int]], explain: bool) -> List[str]:
    """Disassembles the given list of machine code entries, returning a list of menmonics."""
    ret = []

    vsh_ins = vsh_instruction.VshInstruction()
    for instruction in values:
        vsh_ins.set_values(instruction)

        disassembled = vsh_ins.disassemble()
        if explain:
            disassembled += "\n/*" + vsh_ins.explain() + "\n*/"
        ret.append(disassembled)

    return ret


def disassemble_to_instructions(
    values: List[List[int]],
) -> List[vsh_instruction.VshInstruction]:
    """Converts the given list of machine code instructions to VshInstruction instances."""
    ret = []
    for instruction in values:
        vsh_ins = vsh_instruction.VshInstruction()
        vsh_ins.set_values(instruction)
        ret.append(vsh_ins)
    return ret


def _main(args):
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level)

    if not os.path.isfile(args.input):
        print(f"Failed to open input file '{args.input}'", file=sys.stderr)
        return 1

    if args.text:
        with open(args.input, encoding="utf-8") as infile:
            values = _parse_text_input(infile)
    else:
        with open(args.input, "rb") as infile:
            values = _parse_binary_input(infile)

    results = disassemble(values, args.explain)
    results = "\n".join(results)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as outfile:
            outfile.write(results)
    else:
        print(results)

    return 0


def entrypoint():
    """The main entrypoint for this program."""

    def _parse_args():
        parser = argparse.ArgumentParser()

        parser.add_argument(
            "input",
            metavar="source_path",
            help="Source file to disassemble.",
        )

        parser.add_argument(
            "output",
            nargs="?",
            metavar="target_path",
            help="Path to write the .vsh output.",
        )

        parser.add_argument(
            "-t",
            "--text",
            action="store_true",
            help=(
                "Treat the source file as textual, it must contain a list of "
                "hexadecimal integers separated by commas."
            ),
        )

        parser.add_argument(
            "-e",
            "--explain",
            action="store_true",
            help="Add detailed comments describing the values of the fields.",
        )

        parser.add_argument(
            "-v",
            "--verbose",
            help="Enables verbose logging information",
            action="store_true",
        )

        return parser.parse_args()

    sys.exit(_main(_parse_args()))


if __name__ == "__main__":
    entrypoint()
