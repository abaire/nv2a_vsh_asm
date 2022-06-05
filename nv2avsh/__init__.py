"""Setuptools entrypoint for assembler/disassembler."""
from . import assemble
from . import disassemble
from .nv2a_vsh_asm import vsh_instruction


def run_assemble():
    """Assemble nv2a machine code from assembly code."""
    assemble.entrypoint()


def run_disassemble():
    """Disassemble nv2a machine code into assembly code."""
    disassemble.entrypoint()
