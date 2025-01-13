"""Setuptools entrypoint for assembler/disassembler."""

from nv2a_vsh import assemble, disassemble


def run_assemble():
    """Assemble nv2a machine code from assembly code."""
    assemble.entrypoint()


def run_disassemble():
    """Disassemble nv2a machine code into assembly code."""
    disassemble.entrypoint()
