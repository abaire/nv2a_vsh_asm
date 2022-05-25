"""Handles encoding of nv2a vertex shader operations into machine code.

 * Based on https://github.com/XboxDev/nxdk/blob/c4b69e7a82452c21aa2c62701fd3836755950f58/tools/vp20compiler/prog_instruction.c#L1
 * Mesa 3-D graphics library
 * Version:  7.3
 *
 * Copyright (C) 1999-2008  Brian Paul   All Rights Reserved.
 * Copyright (C) 1999-2009  VMware, Inc.  All Rights Reserved.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a
 * copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included
 * in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
 * OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
 * BRIAN PAUL BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN
 * AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import collections
import ctypes
import enum
from typing import List, Optional, Tuple

from . import vsh_instruction
from .vsh_encoder_defs import *
from .vsh_instruction import vsh_diff_instructions


class Opcode(enum.Enum):
    OPCODE_NOP = enum.auto()
    OPCODE_ADD = enum.auto()
    OPCODE_ARL = enum.auto()
    OPCODE_DP3 = enum.auto()
    OPCODE_DP4 = enum.auto()
    OPCODE_DPH = enum.auto()
    OPCODE_DST = enum.auto()
    OPCODE_EXP = enum.auto()
    OPCODE_LIT = enum.auto()
    OPCODE_LOG = enum.auto()
    OPCODE_MAD = enum.auto()
    OPCODE_MAX = enum.auto()
    OPCODE_MIN = enum.auto()
    OPCODE_MOV = enum.auto()
    OPCODE_MUL = enum.auto()
    OPCODE_RCC = enum.auto()
    OPCODE_RCP = enum.auto()
    OPCODE_RSQ = enum.auto()
    OPCODE_SGE = enum.auto()
    OPCODE_SLT = enum.auto()
    OPCODE_SUB = enum.auto()

    def is_ilu(self) -> bool:
        if self == self.OPCODE_EXP:
            return True
        if self == self.OPCODE_LIT:
            return True
        if self == self.OPCODE_LOG:
            return True
        if self == self.OPCODE_RCC:
            return True
        if self == self.OPCODE_RCP:
            return True
        if self == self.OPCODE_RSQ:
            return True
        return False

    def is_mac(self) -> bool:
        return not self.is_ilu()


def get_writemask_name(value: int) -> str:
    """Returns a pretty printed string for the given write mask."""
    return WRITEMASK_NAME[value]


class RegisterFile(enum.Enum):
    PROGRAM_TEMPORARY = enum.auto()  # machine->Temporary[]
    PROGRAM_INPUT = enum.auto()  # machine->Inputs[]
    PROGRAM_OUTPUT = enum.auto()  # machine->Outputs[]
    PROGRAM_ENV_PARAM = enum.auto()  # gl_program->Parameters[]
    PROGRAM_ADDRESS = enum.auto()  # machine->AddressReg
    PROGRAM_UNDEFINED = enum.auto()  # Invalid/TBD value


class SourceRegister:
    """Models information about a source register."""

    def __init__(
        self,
        file: RegisterFile,
        index: int = 0,
        swizzle: int = SWIZZLE_XYZW,
        rel_addr: bool = False,
        negate: bool = False,
    ):
        self.file = file
        self.index = index
        self.swizzle = swizzle
        self.rel_addr = rel_addr
        self.negate = negate

    def set_negated(self):
        self.negate = True

    def __repr__(self):
        return f"{type(self).__name__}({self.file} {self.index} {vsh_instruction.get_swizzle_name(self.swizzle)})"


class DestinationRegister:
    """Models information about a destination register."""

    def __init__(
        self,
        file: RegisterFile,
        index: int = 0,
        write_mask: int = WRITEMASK_XYZW,
        rel_addr: int = 0,
    ):
        self.file = file
        self.index = index
        self.write_mask = write_mask
        self.rel_addr = rel_addr

    def __repr__(self):
        return f"{type(self).__name__}({self.pretty_string()})"

    def pretty_string(self) -> str:
        return f"{self.file} {self.index}{WRITEMASK_NAME[self.write_mask]}"


class Instruction:
    """Models a single instruction."""

    def __init__(
        self,
        opcode: Opcode,
        dst_reg: Optional[DestinationRegister] = None,
        src_a: Optional[SourceRegister] = None,
        src_b: Optional[SourceRegister] = None,
        src_c: Optional[SourceRegister] = None,
        paired_ilu_opcode: Optional[Opcode] = None,
        paired_ilu_dst_reg: Optional[DestinationRegister] = None,
    ):
        self.opcode = opcode
        self.dst_reg = dst_reg
        self.src_reg = [src_a, src_b, src_c]
        self.paired_ilu_opcode = paired_ilu_opcode
        self.paired_ilu_dst_reg = paired_ilu_dst_reg

    def __repr__(self):
        paired_info = ""
        if self.paired_ilu_opcode:
            assert self.paired_ilu_dst_reg
            paired_info = (
                f" + {self.paired_ilu_opcode}=>{repr(self.paired_ilu_dst_reg)}"
            )

        params = [repr(p) for p in self.src_reg if p]
        return (
            f"<{type(self).__name__} {self.opcode} {repr(self.dst_reg)} "
            + " ".join(params)
            + f"{paired_info}"
            + ">"
        )


def _process_opcode(
    ins: Instruction, out: vsh_instruction.VshInstruction
) -> Tuple[bool, bool]:
    def _set(opcode: Opcode, mov_is_ilu=False):
        ilu = False
        mac = False
        if opcode == Opcode.OPCODE_MOV:
            if mov_is_ilu:
                out.ilu = ILU.ILU_MOV
                ilu = True
            else:
                out.mac = MAC.MAC_MOV
                mac = True

        elif opcode == Opcode.OPCODE_ADD:
            out.mac = MAC.MAC_ADD
            mac = True

        elif opcode == Opcode.OPCODE_ARL:
            out.mac = MAC.MAC_ARL
            mac = True

        elif opcode == Opcode.OPCODE_SUB:
            out.mac = MAC.MAC_ADD
            out.c_negate = True
            mac = True
            raise Exception("TODO: xor negated args")

        elif opcode == Opcode.OPCODE_MAD:
            out.mac = MAC.MAC_MAD
            mac = True

        elif opcode == Opcode.OPCODE_MUL:
            out.mac = MAC.MAC_MUL
            mac = True

        elif opcode == Opcode.OPCODE_MAX:
            out.mac = MAC.MAC_MAX
            mac = True

        elif opcode == Opcode.OPCODE_MIN:
            out.mac = MAC.MAC_MIN
            mac = True

        elif opcode == Opcode.OPCODE_SGE:
            out.mac = MAC.MAC_SGE
            mac = True

        elif opcode == Opcode.OPCODE_SLT:
            out.mac = MAC.MAC_SLT
            mac = True

        elif opcode == Opcode.OPCODE_DP3:
            out.mac = MAC.MAC_DP3
            mac = True

        elif opcode == Opcode.OPCODE_DP4:
            out.mac = MAC.MAC_DP4
            mac = True

        elif opcode == Opcode.OPCODE_DPH:
            out.mac = MAC.MAC_DPH
            mac = True

        elif opcode == Opcode.OPCODE_DST:
            out.mac = MAC.MAC_DST
            mac = True

        elif opcode == Opcode.OPCODE_RCP:
            out.ilu = ILU.ILU_RCP
            ilu = True

        elif opcode == Opcode.OPCODE_RCC:
            out.ilu = ILU.ILU_RCC
            ilu = True

        elif opcode == Opcode.OPCODE_RSQ:
            out.ilu = ILU.ILU_RSQ
            ilu = True

        elif opcode == Opcode.OPCODE_EXP:
            out.ilu = ILU.ILU_EXP
            ilu = True

        elif opcode == Opcode.OPCODE_LOG:
            out.ilu = ILU.ILU_LOG
            ilu = True

        elif opcode == Opcode.OPCODE_LIT:
            out.ilu = ILU.ILU_LIT
            ilu = True

        else:
            raise Exception(f"Invalid opcode for instruction {ins}")

        return ilu, mac

    ilu, mac = _set(ins.opcode)
    if ins.paired_ilu_opcode:
        add_ilu, add_mac = _set(ins.paired_ilu_opcode, True)
        if ilu and add_ilu:
            raise Exception(
                "Paired instructions {ins.opcode} + {ins.paired_opcode} both use the ILU."
            )
        if mac and add_mac:
            raise Exception(
                "Paired instructions {ins.opcode} + {ins.paired_opcode} both use the MAC."
            )
        ilu = True
        mac = True

    return ilu, mac


def _process_destination(
    dst_reg: Optional[DestinationRegister],
    ilu: bool,
    mac: bool,
    vsh_ins: vsh_instruction.VshInstruction,
):
    if not dst_reg:
        return

    if dst_reg.file == RegisterFile.PROGRAM_TEMPORARY:
        vsh_ins.out_temp_reg = dst_reg.index
        if mac:
            vsh_ins.out_mac_mask = VSH_MASK[dst_reg.write_mask]
        elif ilu:
            vsh_ins.out_ilu_mask = VSH_MASK[dst_reg.write_mask]
        return

    if dst_reg.file == RegisterFile.PROGRAM_OUTPUT:
        vsh_ins.out_o_mask = VSH_MASK[dst_reg.write_mask]
        if mac:
            vsh_ins.out_mux = OMUX_MAC
        elif ilu:
            vsh_ins.out_mux = OMUX_ILU

        vsh_ins.out_address = dst_reg.index
        return

    if dst_reg.file == RegisterFile.PROGRAM_ENV_PARAM:
        vsh_ins.out_o_mask = VSH_MASK[dst_reg.write_mask]
        if mac:
            vsh_ins.out_mux = OMUX_MAC
        elif ilu:
            vsh_ins.out_mux = OMUX_ILU

        vsh_ins.out_orb = OUTPUT_C
        vsh_ins.out_address = dst_reg.index
        return

    if dst_reg.file == RegisterFile.PROGRAM_ADDRESS:
        # ARL is the only instruction that can write to A0 and it is MAC-only.
        assert mac

        # The destination is implied by the ARL operand, so nothing needs to be set.
        return

    raise Exception("Unsupported destination target.")


def _process_source(
    ins: Instruction, ilu: bool, mac: bool, vsh_ins: vsh_instruction.VshInstruction
):
    if ilu and not mac:
        # ILU instructions only use input C. Swap src reg 0 and 2.
        assert not ins.src_reg[1]
        assert not ins.src_reg[2]
        ins.src_reg[2] = ins.src_reg[0]
        ins.src_reg[0] = None

    if ins.opcode == Opcode.OPCODE_ADD or ins.opcode == Opcode.OPCODE_SUB:
        # ADD/SUB use A and C. Swap src reg 1 and 2
        assert not ins.src_reg[2]
        ins.src_reg[2] = ins.src_reg[1]
        ins.src_reg[1] = None

    for i, reg in enumerate(ins.src_reg):
        if not reg:
            continue

        if reg.rel_addr:
            vsh_ins.a0x = True

        if reg.file == RegisterFile.PROGRAM_TEMPORARY:
            vsh_ins.set_mux_field(i, PARAM_R)
            vsh_ins.set_temp_reg_field(i, reg.index)
        elif reg.file == RegisterFile.PROGRAM_ENV_PARAM:
            vsh_ins.set_mux_field(i, PARAM_C)
            vsh_ins.const = reg.index
        elif reg.file == RegisterFile.PROGRAM_INPUT:
            vsh_ins.set_mux_field(i, PARAM_V)
            vsh_ins.v = reg.index
        else:
            raise Exception(f"Unsupported register type [{i}]{reg}")

        if reg.negate:
            vsh_ins.set_negate_field(i, True)

        vsh_ins.set_swizzle_field(i, reg.swizzle)


def _process_instruction(ins: Instruction, vsh_ins: vsh_instruction.VshInstruction):
    ilu, mac = _process_opcode(ins, vsh_ins)
    if ins.paired_ilu_dst_reg:
        _process_destination(ins.paired_ilu_dst_reg, True, False, vsh_ins)
        _process_destination(ins.dst_reg, False, True, vsh_ins)
    else:
        _process_destination(ins.dst_reg, ilu, mac, vsh_ins)

    _process_source(ins, ilu, mac, vsh_ins)


def encode_to_objects(
    instructions: List[Instruction], inline_final_flag=False
) -> List[vsh_instruction.VshInstruction]:
    """Encodes the given Instructions into a list ov VshInstruction objects."""
    program = []
    for ins in instructions:
        vsh_ins = vsh_instruction.VshInstruction()
        _process_instruction(ins, vsh_ins)

        program.append(vsh_ins)

    if program:
        if inline_final_flag:
            program[-1].final = True
        else:
            vsh_ins = vsh_instruction.VshInstruction(True)
            program.append(vsh_ins)

    return program


def encode(instructions: List[Instruction], inline_final_flag=False) -> List[List[int]]:
    """Encodes a list of instructions into a list of machine code quadruplets."""
    program = encode_to_objects(instructions, inline_final_flag)
    return [x.encode() for x in program]
