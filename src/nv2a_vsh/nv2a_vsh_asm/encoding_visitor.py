"""Provides an ANTLR visitor that generates vsh instructions."""

# pylint: disable=too-few-public-methods
# pylint: disable=too-many-public-methods
# pylint: disable=useless-return

# Func/arg names are dictated by Antlr generated code.
# ruff: noqa: N802 Function name should be lowercase
# ruff: noqa: N803 Argument name should be lowercase
# ruff: noqa: PLR2004 Magic value used in comparison

from __future__ import annotations

import collections
import re
from typing import TYPE_CHECKING

from nv2a_vsh.grammar.vsh.VshLexer import VshLexer
from nv2a_vsh.grammar.vsh.VshVisitor import VshVisitor
from nv2a_vsh.nv2a_vsh_asm import vsh_encoder, vsh_encoder_defs, vsh_instruction
from nv2a_vsh.nv2a_vsh_asm.encoding_error import EncodingError, EncodingErrorSubtype
from nv2a_vsh.nv2a_vsh_asm.vsh_encoder_defs import InputRegisters, OutputRegisters

if TYPE_CHECKING:
    from antlr4.ParserRuleContext import ParserRuleContext
    from antlr4.Token import CommonToken

    from nv2a_vsh.grammar.vsh.VshParser import VshParser
    from nv2a_vsh.nv2a_vsh_asm.vsh_encoder import Instruction

_DESTINATION_MASK_LOOKUP = {
    ".x": vsh_encoder_defs.WRITEMASK_X,
    ".y": vsh_encoder_defs.WRITEMASK_Y,
    ".xy": vsh_encoder_defs.WRITEMASK_XY,
    ".z": vsh_encoder_defs.WRITEMASK_Z,
    ".xz": vsh_encoder_defs.WRITEMASK_XZ,
    ".yz": vsh_encoder_defs.WRITEMASK_YZ,
    ".xyz": vsh_encoder_defs.WRITEMASK_XYZ,
    ".w": vsh_encoder_defs.WRITEMASK_W,
    ".xw": vsh_encoder_defs.WRITEMASK_XW,
    ".yw": vsh_encoder_defs.WRITEMASK_YW,
    ".xyw": vsh_encoder_defs.WRITEMASK_XYW,
    ".zw": vsh_encoder_defs.WRITEMASK_ZW,
    ".xzw": vsh_encoder_defs.WRITEMASK_XZW,
    ".yzw": vsh_encoder_defs.WRITEMASK_YZW,
    ".xyzw": vsh_encoder_defs.WRITEMASK_XYZW,
}

_NAME_TO_DESTINATION_REGISTER_MAP = {
    "oPos": vsh_encoder_defs.OutputRegisters.REG_POS,
    "oD0": vsh_encoder_defs.OutputRegisters.REG_DIFFUSE,
    "oDiffuse": vsh_encoder_defs.OutputRegisters.REG_DIFFUSE,
    "oD1": vsh_encoder_defs.OutputRegisters.REG_SPECULAR,
    "oSpecular": vsh_encoder_defs.OutputRegisters.REG_SPECULAR,
    "oFog": vsh_encoder_defs.OutputRegisters.REG_FOG_COORD,
    "oPts": vsh_encoder_defs.OutputRegisters.REG_POINT_SIZE,
    "oB0": vsh_encoder_defs.OutputRegisters.REG_BACK_DIFFUSE,
    "oBackDiffuse": vsh_encoder_defs.OutputRegisters.REG_BACK_DIFFUSE,
    "oB1": vsh_encoder_defs.OutputRegisters.REG_BACK_SPECULAR,
    "oBackSpecular": vsh_encoder_defs.OutputRegisters.REG_BACK_SPECULAR,
    "oTex0": vsh_encoder_defs.OutputRegisters.REG_TEX0,
    "oT0": vsh_encoder_defs.OutputRegisters.REG_TEX0,
    "oTex1": vsh_encoder_defs.OutputRegisters.REG_TEX1,
    "oT1": vsh_encoder_defs.OutputRegisters.REG_TEX1,
    "oTex2": vsh_encoder_defs.OutputRegisters.REG_TEX2,
    "oT2": vsh_encoder_defs.OutputRegisters.REG_TEX2,
    "oTex3": vsh_encoder_defs.OutputRegisters.REG_TEX3,
    "oT3": vsh_encoder_defs.OutputRegisters.REG_TEX3,
}

_SWIZZLE_LOOKUP = {
    "x": vsh_encoder_defs.SWIZZLE_X,
    "y": vsh_encoder_defs.SWIZZLE_Y,
    "z": vsh_encoder_defs.SWIZZLE_Z,
    "w": vsh_encoder_defs.SWIZZLE_W,
}

_SOURCE_REGISTER_LOOKUP = {
    "v0": vsh_encoder_defs.InputRegisters.V0,
    "ipos": vsh_encoder_defs.InputRegisters.V0,
    "v1": vsh_encoder_defs.InputRegisters.V1,
    "iweight": vsh_encoder_defs.InputRegisters.V1,
    "v2": vsh_encoder_defs.InputRegisters.V2,
    "inormal": vsh_encoder_defs.InputRegisters.V2,
    "v3": vsh_encoder_defs.InputRegisters.V3,
    "idiffuse": vsh_encoder_defs.InputRegisters.V3,
    "v4": vsh_encoder_defs.InputRegisters.V4,
    "ispecular": vsh_encoder_defs.InputRegisters.V4,
    "v5": vsh_encoder_defs.InputRegisters.V5,
    "ifog": vsh_encoder_defs.InputRegisters.V5,
    "v6": vsh_encoder_defs.InputRegisters.V6,
    "ipts": vsh_encoder_defs.InputRegisters.V6,
    "v7": vsh_encoder_defs.InputRegisters.V7,
    "ibackdiffuse": vsh_encoder_defs.InputRegisters.V7,
    "v8": vsh_encoder_defs.InputRegisters.V8,
    "ibackspecular": vsh_encoder_defs.InputRegisters.V8,
    "v9": vsh_encoder_defs.InputRegisters.V9,
    "itex0": vsh_encoder_defs.InputRegisters.V9,
    "v10": vsh_encoder_defs.InputRegisters.V10,
    "itex1": vsh_encoder_defs.InputRegisters.V10,
    "v11": vsh_encoder_defs.InputRegisters.V11,
    "itex2": vsh_encoder_defs.InputRegisters.V11,
    "v12": vsh_encoder_defs.InputRegisters.V12,
    "itex3": vsh_encoder_defs.InputRegisters.V12,
    "v13": vsh_encoder_defs.InputRegisters.V13,
    "v14": vsh_encoder_defs.InputRegisters.V14,
    "v15": vsh_encoder_defs.InputRegisters.V15,
}

_SOURCE_REGISTER_TO_NAME_MAP = {
    vsh_encoder_defs.InputRegisters.V0: "v0",
    vsh_encoder_defs.InputRegisters.V1: "v1",
    vsh_encoder_defs.InputRegisters.V2: "v2",
    vsh_encoder_defs.InputRegisters.V3: "v3",
    vsh_encoder_defs.InputRegisters.V4: "v4",
    vsh_encoder_defs.InputRegisters.V5: "v5",
    vsh_encoder_defs.InputRegisters.V6: "v6",
    vsh_encoder_defs.InputRegisters.V7: "v7",
    vsh_encoder_defs.InputRegisters.V8: "v8",
    vsh_encoder_defs.InputRegisters.V9: "v9",
    vsh_encoder_defs.InputRegisters.V10: "v10",
    vsh_encoder_defs.InputRegisters.V11: "v11",
    vsh_encoder_defs.InputRegisters.V12: "v12",
    vsh_encoder_defs.InputRegisters.V13: "v13",
    vsh_encoder_defs.InputRegisters.V14: "v14",
    vsh_encoder_defs.InputRegisters.V15: "v15",
}


_RELATIVE_CONSTANT_A_FIRST_RE = re.compile(r"[cC]\s*\[\s*[aA]0\s*\+\s*(\d+)\s*\]")
_RELATIVE_CONSTANT_A_SECOND_RE = re.compile(r"[cC]\s*\[\s*(\d+)\s*\+\s*[aA]0\s*\]")
_REG_CONSTANT = -1


# Maps a uniform type
_UNIFORM_TYPE_TO_SIZE = {
    VshLexer.TYPE_VECTOR: 1,
    VshLexer.TYPE_MATRIX4: 4,
}


def get_text_from_context(ctx: ParserRuleContext) -> str:
    return ctx.start.getInputStream().getText(ctx.start.start, ctx.stop.stop)


class _Uniform:
    """Holds information about a uniform declaration."""

    def __init__(self, identifier: str, type_id: int, value: int):
        self.identifier = identifier
        self.type_id = type_id
        self.value = value
        self.size = _UNIFORM_TYPE_TO_SIZE[type_id]


class _ConstantRegister:
    def __init__(self, index, *, is_relative: bool = False, from_uniform: tuple[str, int] | None = None):
        self.index = index
        self.is_relative = is_relative
        self.from_uniform = from_uniform

    @property
    def type(self):
        """Causes this instance to be treated as a special token type."""
        return _REG_CONSTANT

    def copy_with_offset(self, offset: int) -> _ConstantRegister:
        if self.is_relative:
            msg = f"Cannot add an offset to relative ConstantRegister {self}"
            raise ValueError(msg)
        from_uniform = (self.from_uniform[0], offset) if self.from_uniform else None
        return _ConstantRegister(self.index + offset, is_relative=False, from_uniform=from_uniform)


def _merge_ops(
    ops: list[tuple[vsh_encoder.Instruction, str]],
) -> tuple[tuple[vsh_encoder.Instruction, str] | None, str]:
    """Merges the given list of one or two instructions into a single instruction or error message."""
    if len(ops) == 1:
        return ops[0], ""

    if len(ops) != 2 or ops[0][0].opcode != ops[1][0].opcode:
        return None, "conflicting operations"

    if not ops[0][0].identical_inputs(ops[1][0]):
        return None, "operations have different inputs"

    # Reorder such that the temporary target comes last.
    op = ops[0][0]
    if not op.dst_reg:
        msg = "op.dst_reg must be valid"
        raise ValueError(msg)
    if op.dst_reg.targets_temporary:
        ops = [ops[1], ops[0]]

    # Ensure that there is one output and one temp.
    output_op = ops[0][0]
    if not output_op.dst_reg:
        msg = "output_op.dst_reg must be valid"
        raise ValueError(msg)
    if output_op.dst_reg.targets_temporary:
        return None, "operations both target temporary registers"

    temp_op = ops[1][0]
    if not temp_op.dst_reg:
        msg = "temp_op.dst_reg must be valid"
        raise ValueError(msg)
    if not temp_op.dst_reg.targets_temporary:
        return None, "operations both target output registers"

    output_op.secondary_dst_reg = temp_op.dst_reg
    merged_source = " + ".join([ops[0][1], ops[1][1]])

    return (output_op, merged_source), ""


def _distribute_mov_ops(mov_ops: list[tuple[vsh_encoder.Instruction, str]], mac_ops: list, ilu_ops: list) -> str:
    """Distributes a list of mov ops to the given lists or returns an error message."""

    movs_by_inputs = collections.defaultdict(list)
    for entry in mov_ops:
        op = entry[0]
        movs_by_inputs[op.input_signature()].append(entry)

    if len(movs_by_inputs) > 2:
        return "more than 2 distinct sets of inputs"

    # Merge any paired MOVs.
    output_target = None
    r1_target = None
    temp_target = None

    for movs in movs_by_inputs.values():
        merged, error_message = _merge_ops(movs)
        if error_message:
            return error_message

        if not merged:
            msg = f"_merge_ops(movs = {movs!r}) returned invalid empty result"
            raise ValueError(msg)

        targets_r1 = merged[0].primary_op_targets_r1
        targets_temp = merged[0].primary_op_targets_temporary
        targets_output = merged[0].primary_op_targets_output
        if targets_r1:
            if r1_target:
                return "more than 1 MOV targets R1"
            r1_target = merged
        if targets_output:
            if output_target:
                return "more than 1 MOV targets an output register"
            output_target = merged
        if targets_temp and not targets_r1:
            if temp_target:
                return "more than 1 MOV targets a non-R1 temporary register"
            temp_target = merged

    # If the R1 target also writes to an output register it can be treated as R1 now
    # that output collisions have been resolved.
    if output_target and r1_target and output_target[0] == r1_target[0]:
        output_target = None
    # Similarly, if the temp target aslo writes to the output register, it can be
    # treated as a temp target.
    if output_target and temp_target and output_target[0] == temp_target[0]:
        output_target = None

    has_mac = len(mac_ops) > 0

    # If there's a non-MOV MAC instruction, the MOV must be ILU.
    if has_mac:
        if temp_target:
            return "ILU operation may not target non-R1 temporary registers"
        if output_target:
            output_target[0].swap_inputs_a_c()
            ilu_ops.append(output_target)
        if r1_target:
            r1_target[0].swap_inputs_a_c()
            ilu_ops.append(r1_target)
        return ""

    # If there's a non-MOV ILU instruction, the MOV must be MAC.
    has_ilu = len(ilu_ops) > 0
    if has_ilu:
        if temp_target:
            mac_ops.append(temp_target)
        if output_target:
            mac_ops.append(output_target)
        if r1_target:
            mac_ops.append(r1_target)
        return ""

    # The ILU can only target R1, so if there's another write to a temporary register,
    # it must be a MAC op.
    if temp_target:
        mac_ops.append(temp_target)
        if output_target:
            output_target[0].swap_inputs_a_c()
            ilu_ops.append(output_target)
        elif r1_target:
            r1_target[0].swap_inputs_a_c()
            ilu_ops.append(r1_target)
        return ""

    # At this point there may be two MOVs with distinct inputs, one of which must be
    # output_target and the other must be r1_target. Assign the r1_target to the ILU.
    if r1_target and output_target:
        mac_ops.append(output_target)
        r1_target[0].swap_inputs_a_c()
        ilu_ops.append(r1_target)
        return ""

    # Now there can only be one MOV which must write to both a temp and an output
    if r1_target:
        mac_ops.append(r1_target)
        if output_target or temp_target:
            msg = f"Neither output_target ({output_target!r} nor temp_target {temp_target!r} may be populated"
            raise ValueError(msg)
        return ""

    if temp_target:
        mac_ops.append(r1_target)
        if output_target:
            msg = "output_target must not be set"
            raise ValueError(msg)
        return ""

    msg = "Unexpected MOV processing state"
    raise EncodingError(msg)


def process_combined_operations(
    operations: list[tuple[vsh_encoder.Instruction, str]], start_line: int = 0
) -> tuple[vsh_encoder.Instruction, str]:
    """Combines a set of instructions into a single chained instruction."""
    mac_ops = []
    ilu_ops = []
    mov_ops = []

    for entry in operations:
        op = entry[0]
        if op.opcode == vsh_encoder.Opcode.OPCODE_MOV:
            mov_ops.append(entry)
            continue

        is_ilu = op.opcode.is_ilu()
        if is_ilu:
            entry[0].swap_inputs_a_c()
            ilu_ops.append(entry)
        else:
            opcode = entry[0].opcode
            if opcode in {vsh_encoder.Opcode.OPCODE_ADD, vsh_encoder.Opcode.OPCODE_SUB}:
                entry[0].swap_inputs_b_c()
            mac_ops.append(entry)

    num_mac = len(mac_ops)
    if num_mac > 1:
        merged, error = _merge_ops(mac_ops)
        if error:
            msg = f"Conflicting MAC operations ({error}) at {start_line}"
            raise EncodingError(msg)
        if not merged:
            msg = f"_merge_ops(mac_ops = {mac_ops!r}) returned invalid empty result"
            raise ValueError(msg)
        mac_ops = [merged]

    num_ilu = len(ilu_ops)
    if num_ilu > 1:
        merged, error = _merge_ops(ilu_ops)
        if error:
            msg = f"Conflicting ILU operations ({error}) at {start_line}"
            raise EncodingError(msg)
        if not merged:
            msg = f"_merge_ops(ilu_ops = {ilu_ops!r}) returned invalid empty result"
            raise ValueError(msg)
        ilu_ops = [merged]

    if mov_ops:
        error_message = _distribute_mov_ops(mov_ops, mac_ops, ilu_ops)
        if error_message:
            msg = f"Invalid pairing ({error_message}) at {start_line}"
            raise EncodingError(msg)

    if len(mac_ops) > 1:
        msg = f"Invalid pairing (more than 2 MAC operations) at {start_line}"
        raise EncodingError(msg)
    if len(ilu_ops) > 1:
        msg = f"Invalid pairing (more than 2 ILU operations) at {start_line}"
        raise EncodingError(msg)

    if mac_ops and ilu_ops:
        combined_op = mac_ops[0][0]
        combined_src = mac_ops[0][1]
        ilu_op = ilu_ops[0][0]
        ilu_src = ilu_ops[0][1]

        input_c = combined_op.src_reg[2]

        if input_c and input_c != ilu_op.src_reg[2]:
            msg = "Invalid instruction pairing (MAC operation uses input C which does not match ILU input)"
            raise EncodingError(msg)
        combined_op.src_reg[2] = ilu_op.src_reg[2]
        combined_op.paired_ilu_opcode = ilu_op.opcode
        combined_op.paired_ilu_dst_reg = ilu_op.dst_reg
        combined_op.paired_ilu_secondary_dst_reg = ilu_op.secondary_dst_reg

        combined_src = f"{combined_src} + {ilu_src}"
        combined = combined_op, combined_src

    elif mac_ops:
        combined = mac_ops[0]
    elif ilu_ops:
        combined = ilu_ops[0]
    else:
        msg = "Bad state, mac_ops and ilu_ops empty."
        raise ValueError(msg)

    return combined


class EncodingVisitor(VshVisitor):
    """Visitor that generates a list of vsh instructions."""

    def __init__(self) -> None:
        super().__init__()
        self._uniforms: dict[str, _Uniform] = {}

    def visitStatement(self, ctx: VshParser.StatementContext) -> list[tuple[Instruction, str]]:
        return self.visitChildren(ctx)

    def visitUniform_type(self, ctx: VshParser.Uniform_typeContext):
        if not ctx.children or len(ctx.children) != 1:
            msg = f"Uniform macro missing type type declaration on line {ctx.start.line}\nctx.children {ctx.children!r} must have exactly one element"
            raise ValueError(msg)
        if ctx.children[0].symbol.type not in _UNIFORM_TYPE_TO_SIZE:
            msg = (
                f"ctx.children[0].symbol.type {ctx.children[0].symbol.type!r} must be one of {_UNIFORM_TYPE_TO_SIZE!r}"
            )
            raise ValueError(msg)

        return ctx.children[0].symbol.type

    def visitUniform_declaration(self, ctx: VshParser.Uniform_declarationContext) -> None:
        uniform_type = self.visitChildren(ctx)[0]
        if len(ctx.children) != 3:
            msg = f"ctx.children {ctx.children!r} must have exactly three elements"
            raise ValueError(msg)

        if ctx.children[2].symbol.tokenIndex < 0:
            msg = f"Uniform macro missing constant index on line {ctx.start.line}\nctx.children[2].symbol.tokenIndex = {ctx.children[2].symbol.tokenIndex}"
            raise ValueError(msg)

        identifier = ctx.children[0].symbol.text
        value = int(ctx.children[2].symbol.text)

        if identifier in self._uniforms:
            msg = f"Duplicate definition of uniform {identifier} at line {ctx.start.line}"
            raise EncodingError(msg)
        self._uniforms[identifier] = _Uniform(identifier, uniform_type, value)

    def visitOperation(self, ctx: VshParser.OperationContext) -> tuple[Instruction, str]:
        instructions = self.visitChildren(ctx)
        if len(instructions) != 1:
            msg = f"instructions {instructions!r} must have exactly one element"
            raise ValueError(msg)

        return instructions[0]

    def visitCombined_operation(self, ctx: VshParser.Combined_operationContext):
        operations = self.visitChildren(ctx)
        if len(operations) <= 1 or len(operations) >= 5:
            msg = f"operations {operations!r} must have exactly 2, 3, or 4 elements."
            raise ValueError(msg)

        return process_combined_operations(operations, ctx.start.line)

    def visitOp_add(self, ctx: VshParser.Op_addContext) -> tuple[Instruction, str]:
        operands = self.visitChildren(ctx)
        if len(operands) != 1:
            msg = f"operands {operands!r} must have exactly one element"
            raise ValueError(msg)

        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_ADD, *operands),
            f"add {self._prettify_operands(operands)}",
        )

    def visitOp_arl(self, ctx: VshParser.Op_arlContext) -> tuple[Instruction, str]:
        operands = self.visitChildren(ctx)
        if len(operands) != 1:
            msg = f"operands {operands!r} must have exactly one element"
            raise ValueError(msg)

        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_ARL, *operands),
            f"add {self._prettify_operands(operands)}",
        )

    def visitOp_dp3(self, ctx: VshParser.Op_dp3Context) -> tuple[Instruction, str]:
        operands = self.visitChildren(ctx)
        if len(operands) != 1:
            msg = f"operands {operands!r} must have exactly one element"
            raise ValueError(msg)

        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_DP3, *operands),
            f"dp3 {self._prettify_operands(operands)}",
        )

    def visitOp_dp4(self, ctx: VshParser.Op_dp4Context) -> tuple[Instruction, str]:
        operands = self.visitChildren(ctx)
        if len(operands) != 1:
            msg = f"operands {operands!r} must have exactly one element"
            raise ValueError(msg)

        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_DP4, *operands),
            f"dp4 {self._prettify_operands(operands)}",
        )

    def visitOp_dph(self, ctx: VshParser.Op_dphContext) -> tuple[Instruction, str]:
        operands = self.visitChildren(ctx)
        if len(operands) != 1:
            msg = f"operands {operands!r} must have exactly one element"
            raise ValueError(msg)

        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_DPH, *operands),
            f"dph {self._prettify_operands(operands)}",
        )

    def visitOp_dst(self, ctx: VshParser.Op_dstContext) -> tuple[Instruction, str]:
        operands = self.visitChildren(ctx)
        if len(operands) != 1:
            msg = f"operands {operands!r} must have exactly one element"
            raise ValueError(msg)

        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_DST, *operands),
            f"dst {self._prettify_operands(operands)}",
        )

    def visitOp_expp(self, ctx: VshParser.Op_exppContext) -> tuple[Instruction, str]:
        operands = self.visitChildren(ctx)
        if len(operands) != 1:
            msg = f"operands {operands!r} must have exactly one element"
            raise ValueError(msg)

        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_EXP, *operands),
            f"expp {self._prettify_operands(operands)}",
        )

    def visitOp_lit(self, ctx: VshParser.Op_litContext) -> tuple[Instruction, str]:
        operands = self.visitChildren(ctx)
        if len(operands) != 1:
            msg = f"operands {operands!r} must have exactly one element"
            raise ValueError(msg)

        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_LIT, *operands),
            f"lit {self._prettify_operands(operands)}",
        )

    def visitOp_logp(self, ctx: VshParser.Op_logpContext) -> tuple[Instruction, str]:
        operands = self.visitChildren(ctx)
        if len(operands) != 1:
            msg = f"operands {operands!r} must have exactly one element"
            raise ValueError(msg)

        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_LOG, *operands),
            f"logp {self._prettify_operands(operands)}",
        )

    def visitOp_mad(self, ctx: VshParser.Op_madContext) -> tuple[Instruction, str]:
        operands = self.visitChildren(ctx)
        if len(operands) != 1:
            msg = f"operands {operands!r} must have exactly one element"
            raise ValueError(msg)

        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_MAD, *operands),
            f"mad {self._prettify_operands(operands)}",
        )

    def visitOp_max(self, ctx: VshParser.Op_maxContext) -> tuple[Instruction, str]:
        operands = self.visitChildren(ctx)
        if len(operands) != 1:
            msg = f"operands {operands!r} must have exactly one element"
            raise ValueError(msg)

        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_MAX, *operands),
            f"max {self._prettify_operands(operands)}",
        )

    def visitOp_min(self, ctx: VshParser.Op_minContext) -> tuple[Instruction, str]:
        operands = self.visitChildren(ctx)
        if len(operands) != 1:
            msg = f"operands {operands!r} must have exactly one element"
            raise ValueError(msg)

        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_MIN, *operands),
            f"min {self._prettify_operands(operands)}",
        )

    def visitOp_mov(self, ctx: VshParser.Op_movContext) -> tuple[Instruction, str]:
        operands = self.visitChildren(ctx)
        if len(operands) != 1:
            msg = f"operands {operands!r} must have exactly one element"
            raise ValueError(msg)

        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_MOV, *operands),
            f"mov {self._prettify_operands(operands)}",
        )

    def visitOp_mul(self, ctx: VshParser.Op_mulContext) -> tuple[vsh_encoder.Instruction, str]:
        operands = self.visitChildren(ctx)
        if len(operands) != 1:
            msg = f"operands {operands!r} must have exactly one element"
            raise ValueError(msg)

        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_MUL, *operands),
            f"mul {self._prettify_operands(operands)}",
        )

    def visitOp_rcc(self, ctx: VshParser.Op_rccContext) -> tuple[Instruction, str]:
        operands = self.visitChildren(ctx)
        if len(operands) != 1:
            msg = f"operands {operands!r} must have exactly one element"
            raise ValueError(msg)

        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_RCC, *operands),
            f"rcc {self._prettify_operands(operands)}",
        )

    def visitOp_rcp(self, ctx: VshParser.Op_rcpContext) -> tuple[Instruction, str]:
        operands = self.visitChildren(ctx)
        if len(operands) != 1:
            msg = f"operands {operands!r} must have exactly one element"
            raise ValueError(msg)

        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_RCP, *operands),
            f"rcp {self._prettify_operands(operands)}",
        )

    def visitOp_rsq(self, ctx: VshParser.Op_rsqContext) -> tuple[Instruction, str]:
        operands = self.visitChildren(ctx)
        if len(operands) != 1:
            msg = f"operands {operands!r} must have exactly one element"
            raise ValueError(msg)

        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_RSQ, *operands),
            f"rsq {self._prettify_operands(operands)}",
        )

    def visitOp_sge(self, ctx: VshParser.Op_sgeContext) -> tuple[Instruction, str]:
        operands = self.visitChildren(ctx)
        if len(operands) != 1:
            msg = f"operands {operands!r} must have exactly one element"
            raise ValueError(msg)

        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_SGE, *operands),
            f"sge {self._prettify_operands(operands)}",
        )

    def visitOp_slt(self, ctx: VshParser.Op_sltContext) -> tuple[Instruction, str]:
        operands = self.visitChildren(ctx)
        if len(operands) != 1:
            msg = f"operands {operands!r} must have exactly one element"
            raise ValueError(msg)

        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_SLT, *operands),
            f"slt {self._prettify_operands(operands)}",
        )

    def visitOp_sub(self, ctx: VshParser.Op_subContext) -> tuple[Instruction, str]:
        operands = self.visitChildren(ctx)
        if len(operands) != 1:
            msg = f"operands {operands!r} must have exactly one element"
            raise ValueError(msg)

        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_SUB, *operands),
            f"sub {self._prettify_operands(operands)}",
        )

    def visitP_a0_output(self, ctx: VshParser.P_a0_outputContext):
        target = ctx.children[0].symbol
        mask = None
        if len(ctx.children) > 1:
            mask = ctx.children[1].symbol
        return self._process_output(target, mask)

    def visitP_output(self, ctx: VshParser.P_outputContext):
        operands = self.visitChildren(ctx)
        if operands:
            if len(operands) != 1:
                msg = f"operands {operands!r} must have exactly one element"
                raise ValueError(msg)

            target = operands[0]
            if target.type != _REG_CONSTANT:
                msg = f"target.type { target.type!r} must be _REG_CONSTANT {_REG_CONSTANT!r}"
                raise ValueError(msg)
        else:
            target = ctx.children[0].symbol
        mask = None
        if len(ctx.children) > 1:
            mask = ctx.children[1].symbol
        return self._process_output(target, mask)

    def visitP_input_raw(self, ctx: VshParser.P_input_rawContext):
        subtree = self.visitChildren(ctx)
        source = subtree[0] if subtree else ctx.children[0].symbol
        swizzle = None
        if len(ctx.children) > 1:
            swizzle = ctx.children[1].symbol
        return self._process_input(source, swizzle)

    def visitP_input_negated(self, ctx: VshParser.P_input_negatedContext):
        contents = self.visitChildren(ctx)
        if len(contents) != 1:
            msg = f"contents {contents!r} must have exactly one element"
            raise ValueError(msg)

        src_reg = contents[0]
        src_reg.set_negated()
        return src_reg

    def visitP_input(self, ctx: VshParser.P_inputContext):
        contents = self.visitChildren(ctx)
        return contents[0]

    def visitReg_const(self, ctx: VshParser.Reg_constContext) -> _ConstantRegister:
        reg = ctx.children[0].symbol
        if reg.type == VshLexer.REG_Cx_BARE:
            register = int(reg.text[1:])
            return _ConstantRegister(register)
        if reg.type == VshLexer.REG_Cx_BRACKETED:
            register = int(reg.text[2:-1])
            return _ConstantRegister(register)
        if reg.type == VshLexer.REG_Cx_RELATIVE_A_FIRST:
            match = _RELATIVE_CONSTANT_A_FIRST_RE.match(reg.text)
            if not match:
                msg = f"Failed to parse relative constant {reg.text}"
                raise EncodingError(msg)
            register = int(match.group(1))
            return _ConstantRegister(register, is_relative=True)
        if reg.type == VshLexer.REG_Cx_RELATIVE_A_SECOND:
            match = _RELATIVE_CONSTANT_A_SECOND_RE.match(reg.text)
            if not match:
                msg = f"Failed to parse relative constant {reg.text}"
                raise EncodingError(msg)
            register = int(match.group(1))
            return _ConstantRegister(register, is_relative=True)

        msg = f"TODO: Implement unhandled const register format {reg.text}"
        raise EncodingError(msg)

    def visitUniform_const(self, ctx: VshParser.Uniform_constContext):
        name = ctx.children[0].symbol.text
        uniform: _Uniform | None = self._uniforms.get(name)
        if not uniform:
            msg = f"Undefined uniform {name} used at line {ctx.start.line}"
            raise EncodingError(msg, subtype=EncodingErrorSubtype.UNDEFINED_UNIFORM)

        offset = 0
        if len(ctx.children) > 1:
            offset = int(ctx.children[2].symbol.text)

        if offset >= uniform.size:
            msg = f"Uniform offset out of range (max is {uniform.size - 1}) at line {ctx.start.line}"
            raise EncodingError(msg, subtype=EncodingErrorSubtype.UNIFORM_OFFSET_OUT_OF_RANGE)

        return _ConstantRegister(uniform.value + offset, from_uniform=(name, offset))

    def visitMacro_matrix_4x4_multiply(
        self, ctx: VshParser.Macro_matrix_4x4_multiplyContext
    ) -> list[tuple[Instruction, str]]:
        usage = f"  Usage: {ctx.children[0].symbol.text} <destination> <source> <matrix_uniform>"
        try:
            operands = self.visitChildren(ctx)
        except TypeError as err:
            msg = f"Invalid parameters to {ctx.children[0].symbol.text} on line {ctx.start.line}: '{get_text_from_context(ctx)}'.\n{usage}"
            raise ValueError(msg) from err
        except EncodingError as err:
            if err.subtype == EncodingErrorSubtype.UNDEFINED_UNIFORM:
                msg = f"Invalid matrix uniform parameter on line {ctx.start.line}: '{get_text_from_context(ctx)}'.\n{usage}"
            else:
                msg = f"Invalid parameters to {ctx.children[0].symbol.text} on line {ctx.start.line}: '{get_text_from_context(ctx)}'.\n{usage}"
            raise ValueError(msg) from err

        matrix_uniform = operands[2]
        uniform = matrix_uniform.from_uniform
        if uniform:
            uniform_name, uniform_offset = uniform
            uniform_def = self._uniforms.get(uniform_name)
            if not uniform_def or uniform_def.size != 4:
                msg = f"Invalid matrix uniform type on line {ctx.start.line}: '{get_text_from_context(ctx)}'. Uniform must be matrix type.\n{usage}"
                raise ValueError(msg)
            if uniform_offset:
                msg = f"Invalid matrix uniform offset on line {ctx.start.line}: '{get_text_from_context(ctx)}'. Uniform must be referenced at offset 0.\n{usage}"
                raise ValueError(msg)

        destination_register = operands[0]
        source_register = operands[1]

        destination_x = destination_register.copy_with_mask(vsh_encoder_defs.WRITEMASK_X)
        destination_y = destination_register.copy_with_mask(vsh_encoder_defs.WRITEMASK_Y)
        destination_z = destination_register.copy_with_mask(vsh_encoder_defs.WRITEMASK_Z)
        destination_w = destination_register.copy_with_mask(vsh_encoder_defs.WRITEMASK_W)

        matrix_0 = self._process_input(matrix_uniform.copy_with_offset(0))
        matrix_1 = self._process_input(matrix_uniform.copy_with_offset(1))
        matrix_2 = self._process_input(matrix_uniform.copy_with_offset(2))
        matrix_3 = self._process_input(matrix_uniform.copy_with_offset(3))

        return [
            (
                vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_DP4, destination_x, source_register, matrix_0),
                f"dp4 {self._prettify_operands([destination_x, source_register, matrix_0])}",
            ),
            (
                vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_DP4, destination_y, source_register, matrix_1),
                f"dp4 {self._prettify_operands([destination_y, source_register, matrix_1])}",
            ),
            (
                vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_DP4, destination_z, source_register, matrix_2),
                f"dp4 {self._prettify_operands([destination_z, source_register, matrix_2])}",
            ),
            (
                vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_DP4, destination_w, source_register, matrix_3),
                f"dp4 {self._prettify_operands([destination_w, source_register, matrix_3])}",
            ),
        ]

    @staticmethod
    def _process_destination_mask(mask):
        if not mask:
            return vsh_encoder.WRITEMASK_XYZW

        return _DESTINATION_MASK_LOOKUP[mask.text.lower()]

    def _process_output(self, target, mask):
        mask = self._process_destination_mask(mask)

        if target.type == VshLexer.REG_Rx:
            register = int(target.text[1:])
            return vsh_encoder.DestinationRegister(vsh_encoder.RegisterFile.PROGRAM_TEMPORARY, register, mask)

        if target.type == VshLexer.REG_OUTPUT:
            register = _NAME_TO_DESTINATION_REGISTER_MAP[target.text]
            return vsh_encoder.DestinationRegister(vsh_encoder.RegisterFile.PROGRAM_OUTPUT, register, mask)

        if target.type == VshLexer.REG_A0:
            return vsh_encoder.DestinationRegister(
                vsh_encoder.RegisterFile.PROGRAM_ADDRESS,
                vsh_encoder_defs.OutputRegisters.REG_A0,
                mask,
            )

        if target.type == _REG_CONSTANT:
            if target.is_relative:
                # TODO: Check if this is supported in the HW.
                # Then implement or update grammar to disallow.
                msg = "Unsupported write to relative constant register."
                raise EncodingError(msg)
            return vsh_encoder.DestinationRegister(
                vsh_encoder.RegisterFile.PROGRAM_ENV_PARAM,
                target.index,
                mask,
            )

        msg = f"Unsupported output target '{target.text}' at {target.line}:{target.column}"
        raise EncodingError(msg)

    @staticmethod
    def _process_source_swizzle(swizzle: CommonToken | None) -> int:
        if not swizzle:
            return vsh_encoder_defs.SWIZZLE_XYZW

        # ".zzzz"
        swizzle_elements = swizzle.text[1:].lower()
        elements = [_SWIZZLE_LOOKUP[c] for c in swizzle_elements]
        return vsh_encoder.make_swizzle(*elements)

    def _process_input(self, source, swizzle_token: CommonToken | None = None):
        swizzle = self._process_source_swizzle(swizzle_token)

        if source.type in {VshLexer.REG_Rx, VshLexer.REG_R12}:
            register = int(source.text[1:])
            return vsh_encoder.SourceRegister(vsh_encoder.RegisterFile.PROGRAM_TEMPORARY, register, swizzle)

        if source.type == VshLexer.REG_INPUT:
            register = _SOURCE_REGISTER_LOOKUP[source.text.lower()]
            return vsh_encoder.SourceRegister(vsh_encoder.RegisterFile.PROGRAM_INPUT, register, swizzle)

        if source.type == _REG_CONSTANT:
            return vsh_encoder.SourceRegister(
                vsh_encoder.RegisterFile.PROGRAM_ENV_PARAM,
                source.index,
                swizzle,
                rel_addr=source.is_relative,
            )

        msg = f"Unsupported input register '{source.text}' at {source.line}:{source.column}"
        raise EncodingError(msg)

    def aggregateResult(self, aggregate, nextResult):
        if nextResult is None:
            return aggregate

        if aggregate is None:
            aggregate = []
        aggregate.append(nextResult)
        return aggregate

    @staticmethod
    def _prettify_destination(register: vsh_encoder.DestinationRegister) -> str:
        mask = vsh_encoder.get_writemask_name(register.write_mask)

        if register.file == vsh_encoder.RegisterFile.PROGRAM_TEMPORARY:
            return f"r{register.index}{mask}"

        if register.file in {
            vsh_encoder.RegisterFile.PROGRAM_OUTPUT,
            vsh_encoder.RegisterFile.PROGRAM_ADDRESS,
        }:
            name = vsh_encoder_defs.DESTINATION_REGISTER_TO_NAME_MAP[OutputRegisters(register.index)]
            return f"{name}{mask}"

        if register.file == vsh_encoder.RegisterFile.PROGRAM_ENV_PARAM:
            return f"c[{register.index}]{mask}"

        msg = "TODO: Implement destination register prettification."
        raise EncodingError(msg)

    @staticmethod
    def _prettify_source(register: vsh_encoder.SourceRegister) -> str:
        swizzle = vsh_instruction.get_swizzle_name(register.swizzle)
        swizzle = "" if swizzle == "xyzw" else f".{swizzle}"

        prefix = ""
        if register.negate:
            prefix = "-"

        if register.file == vsh_encoder.RegisterFile.PROGRAM_TEMPORARY:
            return f"{prefix}r{register.index}{swizzle}"

        if register.file == vsh_encoder.RegisterFile.PROGRAM_ENV_PARAM:
            return f"{prefix}c{register.index}{swizzle}"

        if register.file == vsh_encoder.RegisterFile.PROGRAM_INPUT:
            name = _SOURCE_REGISTER_TO_NAME_MAP[InputRegisters(register.index)]
            return f"{prefix}{name}{swizzle}"

        msg = "TODO: Implement destination register prettification."
        raise EncodingError(msg)

    def _prettify_operands(self, operands: list) -> str:
        num_operands = len(operands)
        if not num_operands:
            return ""

        elements = [self._prettify_destination(operands[0])]
        elements.extend([self._prettify_source(src) for src in operands[1:]])

        return ", ".join(elements)
