#!/usr/bin/env python3

"""Assembles nv2a vertex shader machine code."""

# ruff: noqa: T201 `print` found

from __future__ import annotations

import argparse
import logging
import os
import sys

from nv2a_vsh.nv2a_vsh_asm.assembler import Assembler


def assemble_to_c(source: str, *, explicit_final: bool = False) -> tuple[str, list[Assembler.ErrorContext]]:
    """Assembles the given source string, returning a C-style list of values."""
    asm = Assembler(source)
    success = asm.assemble(inline_final_flag=(not explicit_final))
    if not success:
        return "", asm.errors

    results = asm.get_c_output()
    return results, []


def assemble(source: str, *, explicit_final: bool = False) -> tuple[list[list[int]], list[Assembler.ErrorContext]]:
    """Assembles the given source string, returning a list of machine code entries."""
    asm = Assembler(source)
    success = asm.assemble(inline_final_flag=(not explicit_final))
    if not success:
        return [], asm.errors
    results = asm.output
    return results, []


def _main(args):
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level)

    input_file = os.path.abspath(os.path.expanduser(args.input))
    if not os.path.isfile(input_file):
        print(f"Failed to open input file '{args.input}'", file=sys.stderr)
        return 1

    with open(input_file) as infile:
        source = infile.read()
    results, errors = assemble_to_c(source, explicit_final=args.explicit_final)
    if errors:
        print(f"Assembly failed due to errors in {args.input}:", file=sys.stderr)
        for error in errors:
            print(
                f"{args.input}:{error.line}:{error.column}: {error.message}",
                file=sys.stderr,
            )
        return 1

    if args.output:
        with open(args.output, "w") as outfile:
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
            help="Source file to assemble.",
        )

        parser.add_argument(
            "output",
            nargs="?",
            metavar="target_path",
            help="Path to write the .inl output.",
        )

        parser.add_argument(
            "-e",
            "--explicit-final",
            action="store_true",
            help="Append a nop instruction instead of marking the last real instruction as FINAL",
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
