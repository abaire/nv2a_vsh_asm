"""Setuptools entrypoint for assembler/disassembler."""
from . import assemble
from . import disassemble


def run_assemble():
    """Assemble nv2a machine code from assembly code."""
    assemble.entrypoint()


def run_disassemble():
    """Disassemble nv2a machine code into assembly code."""
    disassemble.entrypoint()
