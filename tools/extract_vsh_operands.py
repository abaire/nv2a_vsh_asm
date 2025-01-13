#!/usr/bin/env python3

"""
Processes the source code for xemu vertex shaders and extracts any nv2a
operations.
"""

from __future__ import annotations

import re
import sys

OPCODE_RE = re.compile(r"\s*/\* Slot \d+:\s*(.+) \*/")
ASSEMBLY_RE = re.compile(r"\s*([A-Z]\w+\(.+\));")
BAD_COMMA_RE = re.compile(r"([A-Z]+)\(([^,]+),(\S.+)\)")


def _process_operations(operations) -> list[str]:
    processed = set()

    ret: list[str] = []

    for operation in operations:
        expected_output = operation[0].replace(r" ", ", ")
        if expected_output in processed:
            continue
        processed.add(expected_output)

        prefix = ""
        for param in operation[1:]:
            match = BAD_COMMA_RE.match(param)
            if not match:
                param = param.replace("(", " ").replace(")", " ")  # noqa: PLW2901 loop variable overwritten
            else:
                param = f"{match.group(1)} {match.group(2)}.{match.group(3)}"  # noqa: PLW2901 loop variable overwritten

            ret.append(f"{prefix}{param}")
            prefix = "+ "
        ret.append(f"// [{expected_output}]")
        ret.append("")
    return ret


def _process_file(infile) -> list[str]:
    operations = []

    operation = []
    in_instruction = False

    for line in infile:
        line = line.strip()  # noqa: PLW2901 loop variable overwritten

        if not in_instruction:
            match = OPCODE_RE.match(line)
            if not match:
                continue
            operation = [match.group(1)]
            in_instruction = True
            continue

        match = ASSEMBLY_RE.match(line)
        if not match:
            operations.append(operation)
            operation = []
            in_instruction = False
            continue
        operation.append(match.group(1))

    if operation:
        operations.append(operation)

    return _process_operations(operations)


def _main(filename):
    with open(filename) as infile:
        lines = _process_file(infile)
        for line in lines:
            print(line)  # noqa: T201 `print` found


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1]))
