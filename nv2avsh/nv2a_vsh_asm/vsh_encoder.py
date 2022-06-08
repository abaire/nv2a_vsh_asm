# pylint: disable=line-too-long
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
# pylint: enable=line-too-long

# pylint: disable=too-few-public-methods
# pylint: disable=too-many-arguments
# pylint: disable=too-many-branches
# pylint: disable=too-many-return-statements
# pylint: disable=too-many-statements
# pylint: disable=unused-wildcard-import
# pylint: disable=wildcard-import

import sys
from typing import List, Optional, Tuple

from . import vsh_instruction
from .vsh_encoder_defs import *
from .encoding_error import EncodingError


class Opcode(enum.Enum):
    """Enumerates all supported opcodes."""

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
        """Returns True if this opcode is an ILU operation."""
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
        """Returns True if this opcode is a MAC operation."""
        return not self.is_ilu()


def get_writemask_name(value: int) -> str:
    """Returns a pretty printed string for the given write mask."""
    return WRITEMASK_NAME[value]


class RegisterFile(enum.Enum):
    """Logical groupings of I/O registers."""

    PROGRAM_TEMPORARY = enum.auto()  # r* registers
    PROGRAM_INPUT = enum.auto()  # v* registers
    PROGRAM_OUTPUT = enum.auto()  # o* registers
    PROGRAM_ENV_PARAM = enum.auto()  # c* references
    PROGRAM_ADDRESS = enum.auto()  # a0
    PROGRAM_UNDEFINED = enum.auto()


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
        self.file: RegisterFile = file
        self.index: int = index
        self.swizzle: int = swizzle
        self.rel_addr: bool = rel_addr
        self.negate: bool = negate

    def set_negated(self):
        """This register's value should be negated."""
        self.negate = True

    def as_tuple(self):
        """Returns the contents of this destination register as a tuple."""
        return (self.file, self.index, self.swizzle, self.rel_addr, self.negate)

    def __eq__(self, other):
        if not isinstance(other, SourceRegister):
            return NotImplemented
        return other.as_tuple() == self.as_tuple()

    def __repr__(self):
        return (
            f"{type(self).__name__}({self.file} "
            f"{self.index} "
            f"{vsh_instruction.get_swizzle_name(self.swizzle)})"
        )


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

    @property
    def targets_temporary(self):
        """Whether this destination is one of the temporary (Rx) registers."""
        return self.file == RegisterFile.PROGRAM_TEMPORARY

    def as_tuple(self):
        """Returns the contents of this destination register as a tuple."""
        return (self.file, self.index, self.write_mask, self.rel_addr)

    def __hash__(self):
        return hash(self.as_tuple())

    def __eq__(self, other):
        if not isinstance(other, DestinationRegister):
            return NotImplemented
        return other.as_tuple() == self.as_tuple()

    def __repr__(self):
        return f"{type(self).__name__}({self.pretty_string()})"

    def pretty_string(self) -> str:
        """Returns a pretty-printed string describing this destination register."""
        return f"{self.file} {self.index}{WRITEMASK_NAME[self.write_mask]}"


class Instruction:
    """Models a single instruction."""

    def __init__(
        self,
        opcode: Opcode,
        output: Optional[DestinationRegister] = None,
        src_a: Optional[SourceRegister] = None,
        src_b: Optional[SourceRegister] = None,
        src_c: Optional[SourceRegister] = None,
        secondary_output: Optional[DestinationRegister] = None,
        paired_ilu_opcode: Optional[Opcode] = None,
        paired_ilu_dst_reg: Optional[DestinationRegister] = None,
        paired_ilu_secondary_dst_reg: Optional[DestinationRegister] = None,
    ):
        self.opcode = opcode
        self.dst_reg = output
        self.secondary_dst_reg = secondary_output
        self.src_reg = [src_a, src_b, src_c]
        self.paired_ilu_opcode = paired_ilu_opcode
        self.paired_ilu_dst_reg = paired_ilu_dst_reg
        self.paired_ilu_secondary_dst_reg = paired_ilu_secondary_dst_reg

    @property
    def primary_op_targets_r1(self) -> bool:
        """Returns True if the primary operation targets the R1 register."""
        for reg in [self.dst_reg, self.secondary_dst_reg]:
            if not reg:
                continue
            if reg.targets_temporary and reg.index == 1:
                return True
        return False

    @property
    def primary_op_targets_temporary(self) -> bool:
        """Returns True if the primary operation targets any temporary register."""
        for reg in [self.dst_reg, self.secondary_dst_reg]:
            if not reg:
                continue
            if reg.targets_temporary:
                return True
        return False

    @property
    def primary_op_targets_output(self) -> bool:
        """Returns True if the primary operation targets an output (o or c) register."""
        for reg in [self.dst_reg, self.secondary_dst_reg]:
            if not reg:
                continue
            if not reg.targets_temporary:
                return True
        return False

    def input_signature(self) -> Tuple:
        """Returns a tuple describing the inputs to this operation."""
        elements = []
        for src in self.src_reg:
            if not src:
                elements.append(src)
                continue
            elements.append(src.as_tuple())
        return tuple(elements)

    def identical_inputs(self, other) -> bool:
        """Returns True if `other` has the same src_reg's as this Instruction."""
        return other.input_signature() == self.input_signature()

    def swap_inputs_a_c(self):
        """Swaps the A and C inputs (e.g., for an ILU instruction)."""
        self.src_reg = [self.src_reg[2], self.src_reg[1], self.src_reg[0]]

    def swap_inputs_b_c(self):
        """Swaps the B and C inputs (e.g., for an ADD instruction)."""
        self.src_reg = [self.src_reg[0], self.src_reg[2], self.src_reg[1]]

    def __eq__(self, other) -> bool:
        if not isinstance(other, Instruction):
            return False

        return (
            other.opcode == self.opcode
            and other.dst_reg == self.dst_reg
            and other.secondary_dst_reg == self.secondary_dst_reg
            and other.paired_ilu_opcode == self.paired_ilu_opcode
            and other.paired_ilu_dst_reg == self.paired_ilu_dst_reg
            and other.paired_ilu_secondary_dst_reg == self.paired_ilu_secondary_dst_reg
            and self.identical_inputs(other)
        )

    def __repr__(self) -> str:
        paired_info = ""
        if self.paired_ilu_opcode:
            assert self.paired_ilu_dst_reg
            secondary_output = ""
            if self.paired_ilu_secondary_dst_reg:
                secondary_output = f"+{repr(self.paired_ilu_secondary_dst_reg)}"
            paired_info = f" + {self.paired_ilu_opcode}=>{repr(self.paired_ilu_dst_reg)}{secondary_output}"

        params = [repr(p) for p in self.src_reg if p]
        secondary_output = ""
        if self.secondary_dst_reg:
            secondary_output = f"+{repr(self.secondary_dst_reg)}"
        return (
            f"<{type(self).__name__} {self.opcode} {repr(self.dst_reg)}{secondary_output} "
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
            raise EncodingError("TODO: xor negated args")

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
            raise EncodingError(f"Invalid opcode for instruction {ins}")

        return ilu, mac

    ilu, mac = _set(ins.opcode)
    if ins.paired_ilu_opcode:
        add_ilu, add_mac = _set(ins.paired_ilu_opcode, True)
        if ilu and add_ilu:
            raise EncodingError(
                "Paired instructions {ins.opcode} + {ins.paired_opcode} both use the ILU."
            )
        if mac and add_mac:
            raise EncodingError(
                "Paired instructions {ins.opcode} + {ins.paired_opcode} both use the MAC."
            )
        ilu = True
        mac = True

    return ilu, mac


def _process_destination(
    dst_reg: Optional[DestinationRegister],
    secondary_dst_reg: Optional[DestinationRegister],
    ilu: bool,
    mac: bool,
    vsh_ins: vsh_instruction.VshInstruction,
    is_paired: bool = False,
):
    if not dst_reg:
        assert not secondary_dst_reg
        return

    def _process(reg: DestinationRegister):
        if reg.file == RegisterFile.PROGRAM_TEMPORARY:
            if is_paired and ilu and reg.index != 1:
                # TODO: Implement a better system for tracking warnings.
                print(
                    f"Warning: Paired ILU instruction writes to R{reg.index} but will silently be treated as an R1 write. Emitting R1 target.",
                    file=sys.stderr,
                )
                vsh_ins.out_temp_reg = 1
            else:
                vsh_ins.out_temp_reg = reg.index
            if mac:
                vsh_ins.out_mac_mask = VSH_MASK[reg.write_mask]
            elif ilu:
                vsh_ins.out_ilu_mask = VSH_MASK[reg.write_mask]
            return

        if reg.file == RegisterFile.PROGRAM_OUTPUT:
            vsh_ins.out_o_mask = VSH_MASK[reg.write_mask]
            if mac:
                vsh_ins.out_mux = OMUX_MAC
            elif ilu:
                vsh_ins.out_mux = OMUX_ILU

            vsh_ins.out_address = reg.index
            return

        if reg.file == RegisterFile.PROGRAM_ENV_PARAM:
            vsh_ins.out_o_mask = VSH_MASK[reg.write_mask]
            if mac:
                vsh_ins.out_mux = OMUX_MAC
            elif ilu:
                vsh_ins.out_mux = OMUX_ILU

            vsh_ins.out_o_or_c = OUTPUT_C
            vsh_ins.out_address = reg.index
            return

        if reg.file == RegisterFile.PROGRAM_ADDRESS:
            # ARL is the only instruction that can write to A0 and it is MAC-only.
            assert mac

            # The destination is implied by the ARL operand, so nothing needs to be set.
            return

        raise EncodingError(f"Unsupported destination register {reg}.")

    _process(dst_reg)
    if secondary_dst_reg:
        _process(secondary_dst_reg)


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

    c_reg_index = None
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
            vsh_ins.const_reg = reg.index
            if c_reg_index is not None and c_reg_index != reg.index:
                raise EncodingError(
                    f"Operation reads from more than one C register (c[{c_reg_index}] and c[{reg.index}])"
                )
            c_reg_index = reg.index
        elif reg.file == RegisterFile.PROGRAM_INPUT:
            vsh_ins.set_mux_field(i, PARAM_V)
            vsh_ins.input_reg = reg.index
        else:
            raise EncodingError(f"Unsupported register type [{i}]{reg}")

        if reg.negate:
            vsh_ins.set_negate_field(i, True)

        vsh_ins.set_swizzle_fields(i, reg.swizzle)


def _process_instruction(ins: Instruction, vsh_ins: vsh_instruction.VshInstruction):
    ilu, mac = _process_opcode(ins, vsh_ins)
    if ins.paired_ilu_dst_reg:
        _process_destination(
            ins.paired_ilu_dst_reg,
            ins.paired_ilu_secondary_dst_reg,
            True,
            False,
            vsh_ins,
            True,
        )
        _process_destination(
            ins.dst_reg, ins.secondary_dst_reg, False, True, vsh_ins, True
        )
    else:
        _process_destination(ins.dst_reg, ins.secondary_dst_reg, ilu, mac, vsh_ins)

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
