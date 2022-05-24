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


class InputRegisters(enum.IntEnum):
    """Defines the valid input registers for nv2a hardware."""

    REG_POS = 0
    V0 = 0
    REG_WEIGHT = 1
    V1 = 1
    REG_NORMAL = 2
    V2 = 2
    REG_DIFFUSE = 3
    V3 = 3
    REG_SPECULAR = 4
    V4 = 4
    REG_FOG_COORD = 5
    V5 = 5
    REG_POINT_SIZE = 6
    V6 = 6
    REG_BACK_DIFFUSE = 7
    V7 = 7
    REG_BACK_SPECULAR = 8
    V8 = 8
    REG_TEX0 = 9
    V9 = 9
    REG_TEX1 = 10
    V10 = 10
    REG_TEX2 = 11
    V11 = 11
    REG_TEX3 = 12
    V12 = 12
    V13 = 13
    V14 = 14
    V15 = 15


class OutputRegisters(enum.IntEnum):
    """Defines the valid output registers for nv2a hardware."""

    REG_POS = 0
    # REG_WEIGHT = 1
    # REG_NORMAL = 2
    REG_DIFFUSE = 3
    REG_SPECULAR = 4
    REG_FOG_COORD = 5
    REG_POINT_SIZE = 6
    REG_BACK_DIFFUSE = 7
    REG_BACK_SPECULAR = 8
    REG_TEX0 = 9
    REG_TEX1 = 10
    REG_TEX2 = 11
    REG_TEX3 = 12
    # REG_13 = 13
    # REG_14 = 14


def make_swizzle(
    a: int, b: Optional[int] = None, c: Optional[int] = None, d: Optional[int] = None
) -> int:
    """Creates a swizzle mask from the given components."""
    if b is None:
        b = c = d = a
    elif c is None:
        c = d = b
    elif d is None:
        d = c

    return ((a) << 0) | ((b) << 3) | ((c) << 6) | ((d) << 9)


_SWIZZLE_NAME = {
    SWIZZLE_X: "x",
    SWIZZLE_Y: "y",
    SWIZZLE_Z: "z",
    SWIZZLE_W: "w",
}


def get_swizzle_name(swizzle):
    ret = ""
    for i in range(4):
        ret += _SWIZZLE_NAME[vsh_instruction.get_swizzle(swizzle, i)]
    return ret


SWIZZLE_XYZW = make_swizzle(SWIZZLE_X, SWIZZLE_Y, SWIZZLE_Z, SWIZZLE_W)
SWIZZLE_XXXX = make_swizzle(SWIZZLE_X, SWIZZLE_X, SWIZZLE_X, SWIZZLE_X)
SWIZZLE_YYYY = make_swizzle(SWIZZLE_Y, SWIZZLE_Y, SWIZZLE_Y, SWIZZLE_Y)
SWIZZLE_ZZZZ = make_swizzle(SWIZZLE_Z, SWIZZLE_Z, SWIZZLE_Z, SWIZZLE_Z)
SWIZZLE_WWWW = make_swizzle(SWIZZLE_W, SWIZZLE_W, SWIZZLE_W, SWIZZLE_W)

WRITEMASK_X = 0x1
WRITEMASK_Y = 0x2
WRITEMASK_XY = 0x3
WRITEMASK_Z = 0x4
WRITEMASK_XZ = 0x5
WRITEMASK_YZ = 0x6
WRITEMASK_XYZ = 0x7
WRITEMASK_W = 0x8
WRITEMASK_XW = 0x9
WRITEMASK_YW = 0xA
WRITEMASK_XYW = 0xB
WRITEMASK_ZW = 0xC
WRITEMASK_XZW = 0xD
WRITEMASK_YZW = 0xE
WRITEMASK_XYZW = 0xF

MASK_W = 1
MASK_Z = 2
MASK_ZW = 3
MASK_Y = 4
MASK_YW = 5
MASK_YZ = 6
MASK_YZW = 7
MASK_X = 8
MASK_XW = 9
MASK_XZ = 10
MASK_XZW = 11
MASK_XY = 12
MASK_XYW = 13
MASK_XYZ = 14
MASK_XYZW = 15

_vsh_mask = {
    WRITEMASK_X: MASK_X,
    WRITEMASK_Y: MASK_Y,
    WRITEMASK_XY: MASK_XY,
    WRITEMASK_Z: MASK_Z,
    WRITEMASK_XZ: MASK_XZ,
    WRITEMASK_YZ: MASK_YZ,
    WRITEMASK_XYZ: MASK_XYZ,
    WRITEMASK_W: MASK_W,
    WRITEMASK_XW: MASK_XW,
    WRITEMASK_YW: MASK_YW,
    WRITEMASK_XYW: MASK_XYW,
    WRITEMASK_ZW: MASK_ZW,
    WRITEMASK_XZW: MASK_XZW,
    WRITEMASK_YZW: MASK_YZW,
    WRITEMASK_XYZW: MASK_XYZW,
}

_WRITEMASK_NAME = {
    WRITEMASK_X: ".x",
    WRITEMASK_Y: ".y",
    WRITEMASK_XY: ".xy",
    WRITEMASK_Z: ".z",
    WRITEMASK_XZ: ".xz",
    WRITEMASK_YZ: ".yz",
    WRITEMASK_XYZ: ".xyz",
    WRITEMASK_W: ".w",
    WRITEMASK_XW: ".xw",
    WRITEMASK_YW: ".yw",
    WRITEMASK_XYW: ".xyw",
    WRITEMASK_ZW: ".zw",
    WRITEMASK_XZW: ".xzw",
    WRITEMASK_YZW: ".yzw",
    WRITEMASK_XYZW: "",
}


def get_writemask_name(value: int) -> str:
    """Returns a pretty printed string for the given write mask."""
    return _WRITEMASK_NAME[value]


COND_GT = 1  # greater than zero
COND_EQ = 2  # equal to zero
COND_LT = 3  # less than zero
COND_UN = 4  # unordered (NaN)
COND_GE = 5  # greater than or equal to zero
COND_LE = 6  # less than or equal to zero
COND_NE = 7  # not equal to zero
COND_TR = 8  # always True
COND_FL = 9  # always false

FLOAT32 = 0x1
FLOAT16 = 0x2
FIXED12 = 0x4

SATURATE_OFF = 0
SATURATE_ZERO_ONE = 1

INST_INDEX_BITS = 12


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
        rel_addr: int = 0,
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
        return f"{type(self).__name__}({self.file} {self.index} {get_swizzle_name(self.swizzle)})"


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
        return f"{self.file} {self.index}{_WRITEMASK_NAME[self.write_mask]}"


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


class _VshField(enum.Enum):
    FLD_ILU = enum.auto()
    FLD_MAC = enum.auto()
    FLD_CONST = enum.auto()
    FLD_V = enum.auto()
    FLD_A_NEG = enum.auto()
    FLD_A_SWZ_X = enum.auto()
    FLD_A_SWZ_Y = enum.auto()
    FLD_A_SWZ_Z = enum.auto()
    FLD_A_SWZ_W = enum.auto()
    FLD_A_R = enum.auto()
    FLD_A_MUX = enum.auto()
    FLD_B_NEG = enum.auto()
    FLD_B_SWZ_X = enum.auto()
    FLD_B_SWZ_Y = enum.auto()
    FLD_B_SWZ_Z = enum.auto()
    FLD_B_SWZ_W = enum.auto()
    FLD_B_R = enum.auto()
    FLD_B_MUX = enum.auto()
    FLD_C_NEG = enum.auto()
    FLD_C_SWZ_X = enum.auto()
    FLD_C_SWZ_Y = enum.auto()
    FLD_C_SWZ_Z = enum.auto()
    FLD_C_SWZ_W = enum.auto()
    FLD_C_R_HIGH = enum.auto()
    FLD_C_R_LOW = enum.auto()
    FLD_C_MUX = enum.auto()
    FLD_OUT_MAC_MASK = enum.auto()
    FLD_OUT_R = enum.auto()
    FLD_OUT_ILU_MASK = enum.auto()
    FLD_OUT_O_MASK = enum.auto()
    FLD_OUT_ORB = enum.auto()
    FLD_OUT_ADDRESS = enum.auto()
    FLD_OUT_MUX = enum.auto()
    FLD_A0X = enum.auto()
    FLD_FINAL = enum.auto()
    FLD_C_R = 9999


_FieldMapping = collections.namedtuple(
    "_FieldMapping", ["subtoken", "start_bit", "bit_length"]
)


def _get_field_val(vsh_ins: List[int], mapping: _FieldMapping) -> int:
    val = vsh_ins[mapping.subtoken]
    val >>= mapping.start_bit
    val &= (1 << mapping.bit_length) - 1
    return val


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
        vsh_ins.out_r = dst_reg.index
        if mac:
            vsh_ins.out_mac_mask = _vsh_mask[dst_reg.write_mask]
        elif ilu:
            vsh_ins.out_ilu_mask = _vsh_mask[dst_reg.write_mask]
        return

    if dst_reg.file == RegisterFile.PROGRAM_OUTPUT:
        vsh_ins.out_o_mask = _vsh_mask[dst_reg.write_mask]
        if mac:
            vsh_ins.out_mux = OMUX_MAC
        elif ilu:
            vsh_ins.out_mux = OMUX_ILU

        vsh_ins.out_address = dst_reg.index
        return

    if dst_reg.file == RegisterFile.PROGRAM_ENV_PARAM:
        vsh_ins.out_o_mask = _vsh_mask[dst_reg.write_mask]
        if mac:
            vsh_ins.out_mux = OMUX_MAC
        elif ilu:
            vsh_ins.out_mux = OMUX_ILU

        vsh_ins.out_orb = OUTPUT_C
        vsh_ins.out_address = dst_reg.index
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

        # TODO: A0 rel
        assert not reg.rel_addr

        if reg.file == RegisterFile.PROGRAM_TEMPORARY:
            vsh_ins.set_mux_field(i, PARAM_R)
            vsh_ins.set_reg_field(i, reg.index)
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
            vsh_ins = vsh_instruction.VshInstruction()
            vsh_ins.set_empty_final()
            program.append(vsh_ins)

    return program


def encode(instructions: List[Instruction], inline_final_flag=False) -> List[List[int]]:
    """Encodes a list of instructions into a list of machine code quadruplets."""
    program = encode_to_objects(instructions, inline_final_flag)
    return [x.encode() for x in program]
