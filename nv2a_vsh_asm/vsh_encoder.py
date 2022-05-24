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
import enum
from typing import List, Optional, Tuple

SWIZZLE_X = 0
SWIZZLE_Y = 1
SWIZZLE_Z = 2
SWIZZLE_W = 3
SWIZZLE_ZERO = 4
SWIZZLE_ONE = 5
SWIZZLE_NIL = 7

PARAM_UNKNOWN = 0
PARAM_R = 1
PARAM_V = 2
PARAM_C = 3

OUTPUT_C = 0
OUTPUT_O = 1

OMUX_MAC = 0
OMUX_ILU = 1


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


def _get_swizzle(swz, idx):
    return ((swz) >> ((idx) * 3)) & 0x7


_SWIZZLE_NAME = {
    SWIZZLE_X: "x",
    SWIZZLE_Y: "y",
    SWIZZLE_Z: "z",
    SWIZZLE_W: "w",
}


def get_swizzle_name(swizzle):
    ret = ""
    for i in range(4):
        ret += _SWIZZLE_NAME[_get_swizzle(swizzle, i)]
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

NEGATE_X = 0x1
NEGATE_Y = 0x2
NEGATE_Z = 0x4
NEGATE_W = 0x8
NEGATE_XYZ = 0x7
NEGATE_XYZW = 0xF
NEGATE_NONE = 0x0

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

_Mapping = {
    _VshField.FLD_ILU: _FieldMapping(1, 25, 3),
    _VshField.FLD_MAC: _FieldMapping(1, 21, 4),
    _VshField.FLD_CONST: _FieldMapping(1, 13, 8),
    _VshField.FLD_V: _FieldMapping(1, 9, 4),
    _VshField.FLD_A_NEG: _FieldMapping(1, 8, 1),
    _VshField.FLD_A_SWZ_X: _FieldMapping(1, 6, 2),
    _VshField.FLD_A_SWZ_Y: _FieldMapping(1, 4, 2),
    _VshField.FLD_A_SWZ_Z: _FieldMapping(1, 2, 2),
    _VshField.FLD_A_SWZ_W: _FieldMapping(1, 0, 2),
    _VshField.FLD_A_R: _FieldMapping(2, 28, 4),
    _VshField.FLD_A_MUX: _FieldMapping(2, 26, 2),
    _VshField.FLD_B_NEG: _FieldMapping(2, 25, 1),
    _VshField.FLD_B_SWZ_X: _FieldMapping(2, 23, 2),
    _VshField.FLD_B_SWZ_Y: _FieldMapping(2, 21, 2),
    _VshField.FLD_B_SWZ_Z: _FieldMapping(2, 19, 2),
    _VshField.FLD_B_SWZ_W: _FieldMapping(2, 17, 2),
    _VshField.FLD_B_R: _FieldMapping(2, 13, 4),
    _VshField.FLD_B_MUX: _FieldMapping(2, 11, 2),
    _VshField.FLD_C_NEG: _FieldMapping(2, 10, 1),
    _VshField.FLD_C_SWZ_X: _FieldMapping(2, 8, 2),
    _VshField.FLD_C_SWZ_Y: _FieldMapping(2, 6, 2),
    _VshField.FLD_C_SWZ_Z: _FieldMapping(2, 4, 2),
    _VshField.FLD_C_SWZ_W: _FieldMapping(2, 2, 2),
    _VshField.FLD_C_R_HIGH: _FieldMapping(2, 0, 2),
    # kkjj iiii hhhh gggg ffff eddd dddd dcba
    _VshField.FLD_C_R_LOW: _FieldMapping(3, 30, 2),  # k
    _VshField.FLD_C_MUX: _FieldMapping(3, 28, 2),  # j
    _VshField.FLD_OUT_MAC_MASK: _FieldMapping(3, 24, 4),  # i
    _VshField.FLD_OUT_R: _FieldMapping(3, 20, 4),  # h
    _VshField.FLD_OUT_ILU_MASK: _FieldMapping(3, 16, 4),  # g
    _VshField.FLD_OUT_O_MASK: _FieldMapping(3, 12, 4),  # f
    _VshField.FLD_OUT_ORB: _FieldMapping(3, 11, 1),  # e
    _VshField.FLD_OUT_ADDRESS: _FieldMapping(3, 3, 8),  # d
    _VshField.FLD_OUT_MUX: _FieldMapping(3, 2, 1),  # c
    _VshField.FLD_A0X: _FieldMapping(3, 1, 1),  # b
    _VshField.FLD_FINAL: _FieldMapping(3, 0, 1),  # a
}


def _get_field_val(vsh_ins: List[int], mapping: _FieldMapping) -> int:
    val = vsh_ins[mapping.subtoken]
    val >>= mapping.start_bit
    val &= (1 << mapping.bit_length) - 1
    return val


def vsh_diff_instructions(
    expected: List[int], actual: List[int], ignore_final_flag=False
) -> str:
    """Provides a verbose explanation of the difference of two encoded instructions.

    :return "" if the instructions match, else a string explaining the delta.
    """

    differences = []
    if expected[0] != actual[0]:
        assert expected[0] == 0
        differences.append(f"Invalid instruction, [0](0x{actual[0]:08x} must == 0")

    for field, mapping in _Mapping.items():
        if ignore_final_flag and field == _VshField.FLD_FINAL:
            continue

        e_val = _get_field_val(expected, mapping)
        a_val = _get_field_val(actual, mapping)

        if e_val != a_val:
            name = str(field)[10:]

            differences.append(
                f"{name} 0x{e_val:x} ({e_val:0{mapping.bit_length}b}) != actual 0x{a_val:x} ({a_val:0{mapping.bit_length}b})"
            )

    if not differences:
        return ""

    return (
        (
            "Instructions differ.\n"
            f"\t0x{expected[0]:08x} 0x{expected[1]:08x} 0x{expected[2]:08x} 0x{expected[3]:08x}\n"
            f"\t0x{actual[0]:08x} 0x{actual[1]:08x} 0x{actual[2]:08x} 0x{actual[3]:08x}\n"
            "\n\t"
        )
        + "\n\t".join(differences)
        + "\n"
    )


_mux_field = (_VshField.FLD_A_MUX, _VshField.FLD_B_MUX, _VshField.FLD_C_MUX)
_swizzle_field = (
    (
        _VshField.FLD_A_SWZ_X,
        _VshField.FLD_A_SWZ_Y,
        _VshField.FLD_A_SWZ_Z,
        _VshField.FLD_A_SWZ_W,
    ),
    (
        _VshField.FLD_B_SWZ_X,
        _VshField.FLD_B_SWZ_Y,
        _VshField.FLD_B_SWZ_Z,
        _VshField.FLD_B_SWZ_W,
    ),
    (
        _VshField.FLD_C_SWZ_X,
        _VshField.FLD_C_SWZ_Y,
        _VshField.FLD_C_SWZ_Z,
        _VshField.FLD_C_SWZ_W,
    ),
)
_reg_field = (_VshField.FLD_A_R, _VshField.FLD_B_R, _VshField.FLD_C_R)
_neg_field = (_VshField.FLD_A_NEG, _VshField.FLD_B_NEG, _VshField.FLD_C_NEG)


class ILU(enum.IntEnum):
    ILU_NOP = 0
    ILU_MOV = 1
    ILU_RCP = 2
    ILU_RCC = 3
    ILU_RSQ = 4
    ILU_EXP = 5
    ILU_LOG = 6
    ILU_LIT = 7


class MAC(enum.IntEnum):
    MAC_NOP = 0
    MAC_MOV = 1
    MAC_MUL = 2
    MAC_ADD = 3
    MAC_MAD = 4
    MAC_DP3 = 5
    MAC_DPH = 6
    MAC_DP4 = 7
    MAC_DST = 8
    MAC_MIN = 9
    MAC_MAX = 10
    MAC_SLT = 11
    MAC_SGE = 12
    MAC_ARL = 13


def _vsh_set_field(out: List[int], field_name: _VshField, v: int):
    if field_name == _VshField.FLD_C_R:
        _vsh_set_field(out, _VshField.FLD_C_R_LOW, v & 3)
        _vsh_set_field(out, _VshField.FLD_C_R_HIGH, (v >> 2))
        return

    f = _Mapping[field_name]

    f_bits = (1 << int(f.bit_length)) - 1
    new_val = out[f.subtoken]
    new_val &= ~(f_bits << int(f.start_bit))
    new_val |= (v & f_bits) << f.start_bit
    out[f.subtoken] = new_val


def _process_opcode(ins: Instruction, out: List[int]) -> Tuple[bool, bool]:
    def _set(opcode: Opcode, mov_is_ilu=False):
        ilu = False
        mac = False
        if opcode == Opcode.OPCODE_MOV:
            if mov_is_ilu:
                _vsh_set_field(out, _VshField.FLD_ILU, ILU.ILU_MOV)
                ilu = True
            else:
                _vsh_set_field(out, _VshField.FLD_MAC, MAC.MAC_MOV)
                mac = True

        elif opcode == Opcode.OPCODE_ADD:
            _vsh_set_field(out, _VshField.FLD_MAC, MAC.MAC_ADD)
            mac = True

        elif opcode == Opcode.OPCODE_SUB:
            _vsh_set_field(out, _VshField.FLD_MAC, MAC.MAC_ADD)
            _vsh_set_field(out, _VshField.FLD_C_NEG, 1)
            mac = True
            raise Exception("TODO: xor negated args")

        elif opcode == Opcode.OPCODE_MAD:
            _vsh_set_field(out, _VshField.FLD_MAC, MAC.MAC_MAD)
            mac = True

        elif opcode == Opcode.OPCODE_MUL:
            _vsh_set_field(out, _VshField.FLD_MAC, MAC.MAC_MUL)
            mac = True

        elif opcode == Opcode.OPCODE_MAX:
            _vsh_set_field(out, _VshField.FLD_MAC, MAC.MAC_MAX)
            mac = True

        elif opcode == Opcode.OPCODE_MIN:
            _vsh_set_field(out, _VshField.FLD_MAC, MAC.MAC_MIN)
            mac = True

        elif opcode == Opcode.OPCODE_SGE:
            _vsh_set_field(out, _VshField.FLD_MAC, MAC.MAC_SGE)
            mac = True

        elif opcode == Opcode.OPCODE_SLT:
            _vsh_set_field(out, _VshField.FLD_MAC, MAC.MAC_SLT)
            mac = True

        elif opcode == Opcode.OPCODE_DP3:
            _vsh_set_field(out, _VshField.FLD_MAC, MAC.MAC_DP3)
            mac = True

        elif opcode == Opcode.OPCODE_DP4:
            _vsh_set_field(out, _VshField.FLD_MAC, MAC.MAC_DP4)
            mac = True

        elif opcode == Opcode.OPCODE_DPH:
            _vsh_set_field(out, _VshField.FLD_MAC, MAC.MAC_DPH)
            mac = True

        elif opcode == Opcode.OPCODE_DST:
            _vsh_set_field(out, _VshField.FLD_MAC, MAC.MAC_DST)
            mac = True

        elif opcode == Opcode.OPCODE_RCP:
            _vsh_set_field(out, _VshField.FLD_ILU, ILU.ILU_RCP)
            ilu = True

        elif opcode == Opcode.OPCODE_RCC:
            _vsh_set_field(out, _VshField.FLD_ILU, ILU.ILU_RCC)
            ilu = True

        elif opcode == Opcode.OPCODE_RSQ:
            _vsh_set_field(out, _VshField.FLD_ILU, ILU.ILU_RSQ)
            ilu = True

        elif opcode == Opcode.OPCODE_EXP:
            _vsh_set_field(out, _VshField.FLD_ILU, ILU.ILU_EXP)
            ilu = True

        elif opcode == Opcode.OPCODE_LOG:
            _vsh_set_field(out, _VshField.FLD_ILU, ILU.ILU_LOG)
            ilu = True

        elif opcode == Opcode.OPCODE_LIT:
            _vsh_set_field(out, _VshField.FLD_ILU, ILU.ILU_LIT)
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
    dst_reg: Optional[DestinationRegister], ilu: bool, mac: bool, vsh_ins: List[int]
):
    if not dst_reg:
        return

    if dst_reg.file == RegisterFile.PROGRAM_TEMPORARY:
        _vsh_set_field(vsh_ins, _VshField.FLD_OUT_R, dst_reg.index)
        if mac:
            _vsh_set_field(
                vsh_ins, _VshField.FLD_OUT_MAC_MASK, _vsh_mask[dst_reg.write_mask]
            )
        elif ilu:
            _vsh_set_field(
                vsh_ins, _VshField.FLD_OUT_ILU_MASK, _vsh_mask[dst_reg.write_mask]
            )
        return

    if dst_reg.file == RegisterFile.PROGRAM_OUTPUT:
        _vsh_set_field(vsh_ins, _VshField.FLD_OUT_O_MASK, _vsh_mask[dst_reg.write_mask])
        if mac:
            _vsh_set_field(vsh_ins, _VshField.FLD_OUT_MUX, OMUX_MAC)
        elif ilu:
            _vsh_set_field(vsh_ins, _VshField.FLD_OUT_MUX, OMUX_ILU)

        # TODO: Double check that the index maps to the right output register
        _vsh_set_field(vsh_ins, _VshField.FLD_OUT_ADDRESS, dst_reg.index)
        return

    if dst_reg.file == RegisterFile.PROGRAM_ENV_PARAM:
        _vsh_set_field(vsh_ins, _VshField.FLD_OUT_O_MASK, _vsh_mask[dst_reg.write_mask])
        if mac:
            _vsh_set_field(vsh_ins, _VshField.FLD_OUT_MUX, OMUX_MAC)
        elif ilu:
            _vsh_set_field(vsh_ins, _VshField.FLD_OUT_MUX, OMUX_ILU)

        _vsh_set_field(vsh_ins, _VshField.FLD_OUT_ORB, OUTPUT_C)
        # TODO: the index needs adjustment?
        _vsh_set_field(vsh_ins, _VshField.FLD_OUT_ADDRESS, dst_reg.index)
        return

    raise Exception("Unsupported destination target.")


def _process_source(ins: Instruction, ilu: bool, mac: bool, vsh_ins: List[int]):
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
            _vsh_set_field(vsh_ins, _mux_field[i], PARAM_R)
            _vsh_set_field(vsh_ins, _reg_field[i], reg.index)
        elif reg.file == RegisterFile.PROGRAM_ENV_PARAM:
            _vsh_set_field(vsh_ins, _mux_field[i], PARAM_C)
            # TODO: the index needs ajustment?
            _vsh_set_field(vsh_ins, _VshField.FLD_CONST, reg.index)
        elif reg.file == RegisterFile.PROGRAM_INPUT:
            _vsh_set_field(vsh_ins, _mux_field[i], PARAM_V)
            # TODO: Double check that the index maps to the right input register
            _vsh_set_field(vsh_ins, _VshField.FLD_V, reg.index)
        else:
            raise Exception(f"Unsupported register type [{i}]{reg}")

        if reg.negate == NEGATE_XYZW:
            _vsh_set_field(vsh_ins, _neg_field[i], 1)

        for j in range(4):
            _vsh_set_field(vsh_ins, _swizzle_field[i][j], _get_swizzle(reg.swizzle, j))


def _process_instruction(ins: Instruction, vsh_ins: List[int]):
    ilu, mac = _process_opcode(ins, vsh_ins)
    if ins.paired_ilu_dst_reg:
        _process_destination(ins.paired_ilu_dst_reg, True, False, vsh_ins)
        _process_destination(ins.dst_reg, False, True, vsh_ins)
    else:
        _process_destination(ins.dst_reg, ilu, mac, vsh_ins)

    _process_source(ins, ilu, mac, vsh_ins)


def encode(instructions: List[Instruction], inline_final_flag=False) -> List[List[int]]:
    program = []
    for ins in instructions:
        vsh_ins = [0, 0, 0, 0]
        _vsh_set_field(vsh_ins, _VshField.FLD_ILU, ILU.ILU_NOP)
        _vsh_set_field(vsh_ins, _VshField.FLD_MAC, MAC.MAC_NOP)
        _vsh_set_field(vsh_ins, _VshField.FLD_A_SWZ_X, SWIZZLE_X)
        _vsh_set_field(vsh_ins, _VshField.FLD_A_SWZ_Y, SWIZZLE_Y)
        _vsh_set_field(vsh_ins, _VshField.FLD_A_SWZ_Z, SWIZZLE_Z)
        _vsh_set_field(vsh_ins, _VshField.FLD_A_SWZ_W, SWIZZLE_W)
        _vsh_set_field(vsh_ins, _VshField.FLD_A_MUX, PARAM_V)
        _vsh_set_field(vsh_ins, _VshField.FLD_B_SWZ_X, SWIZZLE_X)
        _vsh_set_field(vsh_ins, _VshField.FLD_B_SWZ_Y, SWIZZLE_Y)
        _vsh_set_field(vsh_ins, _VshField.FLD_B_SWZ_Z, SWIZZLE_Z)
        _vsh_set_field(vsh_ins, _VshField.FLD_B_SWZ_W, SWIZZLE_W)
        _vsh_set_field(vsh_ins, _VshField.FLD_B_MUX, PARAM_V)
        _vsh_set_field(vsh_ins, _VshField.FLD_C_SWZ_X, SWIZZLE_X)
        _vsh_set_field(vsh_ins, _VshField.FLD_C_SWZ_Y, SWIZZLE_Y)
        _vsh_set_field(vsh_ins, _VshField.FLD_C_SWZ_Z, SWIZZLE_Z)
        _vsh_set_field(vsh_ins, _VshField.FLD_C_SWZ_W, SWIZZLE_W)
        _vsh_set_field(vsh_ins, _VshField.FLD_C_MUX, PARAM_V)
        _vsh_set_field(vsh_ins, _VshField.FLD_OUT_R, 7)
        _vsh_set_field(vsh_ins, _VshField.FLD_OUT_ADDRESS, 0xFF)
        _vsh_set_field(vsh_ins, _VshField.FLD_OUT_MUX, OMUX_MAC)
        _vsh_set_field(vsh_ins, _VshField.FLD_OUT_ORB, OUTPUT_O)

        _process_instruction(ins, vsh_ins)

        program.append(vsh_ins)

    if program:
        if inline_final_flag:
            _vsh_set_field(program[-1], _VshField.FLD_FINAL, 1)
        else:
            vsh_ins = [0, 0, 0, 0]
            _vsh_set_field(vsh_ins, _VshField.FLD_FINAL, 1)
            program.append(vsh_ins)

    return program
