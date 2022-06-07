"""Provides an ANTLR visitor that generates vsh instructions."""

# pylint: disable=too-few-public-methods
# pylint: disable=too-many-public-methods
# pylint: disable=useless-return

import collections
import re
from typing import List, Optional, Tuple

from nv2avsh.grammar.vsh.VshLexer import VshLexer
from nv2avsh.grammar.vsh.VshParser import VshParser
from nv2avsh.grammar.vsh.VshVisitor import VshVisitor

from . import vsh_encoder
from . import vsh_encoder_defs
from . import vsh_instruction
from .encoding_error import EncodingError

_DESTINATION_MASK_LOOKUP = {
    ".x": vsh_encoder.WRITEMASK_X,
    ".y": vsh_encoder.WRITEMASK_Y,
    ".xy": vsh_encoder.WRITEMASK_XY,
    ".z": vsh_encoder.WRITEMASK_Z,
    ".xz": vsh_encoder.WRITEMASK_XZ,
    ".yz": vsh_encoder.WRITEMASK_YZ,
    ".xyz": vsh_encoder.WRITEMASK_XYZ,
    ".w": vsh_encoder.WRITEMASK_W,
    ".xw": vsh_encoder.WRITEMASK_XW,
    ".yw": vsh_encoder.WRITEMASK_YW,
    ".xyw": vsh_encoder.WRITEMASK_XYW,
    ".zw": vsh_encoder.WRITEMASK_ZW,
    ".xzw": vsh_encoder.WRITEMASK_XZW,
    ".yzw": vsh_encoder.WRITEMASK_YZW,
    ".xyzw": vsh_encoder.WRITEMASK_XYZW,
}

_NAME_TO_DESTINATION_REGISTER_MAP = {
    "oPos": vsh_encoder.OutputRegisters.REG_POS,
    "oD0": vsh_encoder.OutputRegisters.REG_DIFFUSE,
    "oDiffuse": vsh_encoder.OutputRegisters.REG_DIFFUSE,
    "oD1": vsh_encoder.OutputRegisters.REG_SPECULAR,
    "oSpecular": vsh_encoder.OutputRegisters.REG_SPECULAR,
    "oFog": vsh_encoder.OutputRegisters.REG_FOG_COORD,
    "oPts": vsh_encoder.OutputRegisters.REG_POINT_SIZE,
    "oB0": vsh_encoder.OutputRegisters.REG_BACK_DIFFUSE,
    "oBackDiffuse": vsh_encoder.OutputRegisters.REG_BACK_DIFFUSE,
    "oB1": vsh_encoder.OutputRegisters.REG_BACK_SPECULAR,
    "oBackSpecular": vsh_encoder.OutputRegisters.REG_BACK_SPECULAR,
    "oTex0": vsh_encoder.OutputRegisters.REG_TEX0,
    "oT0": vsh_encoder.OutputRegisters.REG_TEX0,
    "oTex1": vsh_encoder.OutputRegisters.REG_TEX1,
    "oT1": vsh_encoder.OutputRegisters.REG_TEX1,
    "oTex2": vsh_encoder.OutputRegisters.REG_TEX2,
    "oT2": vsh_encoder.OutputRegisters.REG_TEX2,
    "oTex3": vsh_encoder.OutputRegisters.REG_TEX3,
    "oT3": vsh_encoder.OutputRegisters.REG_TEX3,
}

_SWIZZLE_LOOKUP = {
    "x": vsh_encoder.SWIZZLE_X,
    "y": vsh_encoder.SWIZZLE_Y,
    "z": vsh_encoder.SWIZZLE_Z,
    "w": vsh_encoder.SWIZZLE_W,
}

_SOURCE_REGISTER_LOOKUP = {
    "v0": vsh_encoder.InputRegisters.V0,
    "ipos": vsh_encoder.InputRegisters.V0,
    "v1": vsh_encoder.InputRegisters.V1,
    "iweight": vsh_encoder.InputRegisters.V1,
    "v2": vsh_encoder.InputRegisters.V2,
    "inormal": vsh_encoder.InputRegisters.V2,
    "v3": vsh_encoder.InputRegisters.V3,
    "idiffuse": vsh_encoder.InputRegisters.V3,
    "v4": vsh_encoder.InputRegisters.V4,
    "ispecular": vsh_encoder.InputRegisters.V4,
    "v5": vsh_encoder.InputRegisters.V5,
    "ifog": vsh_encoder.InputRegisters.V5,
    "v6": vsh_encoder.InputRegisters.V6,
    "ipts": vsh_encoder.InputRegisters.V6,
    "v7": vsh_encoder.InputRegisters.V7,
    "ibackdiffuse": vsh_encoder.InputRegisters.V7,
    "v8": vsh_encoder.InputRegisters.V8,
    "ibackspecular": vsh_encoder.InputRegisters.V8,
    "v9": vsh_encoder.InputRegisters.V9,
    "itex0": vsh_encoder.InputRegisters.V9,
    "v10": vsh_encoder.InputRegisters.V10,
    "itex1": vsh_encoder.InputRegisters.V10,
    "v11": vsh_encoder.InputRegisters.V11,
    "itex2": vsh_encoder.InputRegisters.V11,
    "v12": vsh_encoder.InputRegisters.V12,
    "itex3": vsh_encoder.InputRegisters.V12,
    "v13": vsh_encoder.InputRegisters.V13,
    "v14": vsh_encoder.InputRegisters.V14,
    "v15": vsh_encoder.InputRegisters.V15,
}

_SOURCE_REGISTER_TO_NAME_MAP = {
    vsh_encoder.InputRegisters.V0: "v0",
    vsh_encoder.InputRegisters.V1: "v1",
    vsh_encoder.InputRegisters.V2: "v2",
    vsh_encoder.InputRegisters.V3: "v3",
    vsh_encoder.InputRegisters.V4: "v4",
    vsh_encoder.InputRegisters.V5: "v5",
    vsh_encoder.InputRegisters.V6: "v6",
    vsh_encoder.InputRegisters.V7: "v7",
    vsh_encoder.InputRegisters.V8: "v8",
    vsh_encoder.InputRegisters.V9: "v9",
    vsh_encoder.InputRegisters.V10: "v10",
    vsh_encoder.InputRegisters.V11: "v11",
    vsh_encoder.InputRegisters.V12: "v12",
    vsh_encoder.InputRegisters.V13: "v13",
    vsh_encoder.InputRegisters.V14: "v14",
    vsh_encoder.InputRegisters.V15: "v15",
}


_RELATIVE_CONSTANT_A_FIRST_RE = re.compile(r"[cC]\s*\[\s*[aA]0\s*\+\s*(\d+)\s*\]")
_RELATIVE_CONSTANT_A_SECOND_RE = re.compile(r"[cC]\s*\[\s*(\d+)\s*\+\s*[aA]0\s*\]")
_REG_CONSTANT = -1


# Maps a uniform type
_UNIFORM_TYPE_TO_SIZE = {
    VshLexer.TYPE_VECTOR: 1,
    VshLexer.TYPE_MATRIX4: 4,
}


class _Uniform:
    """Holds information about a uniform declaration."""

    def __init__(self, identifier: str, type_id: int, value: int):
        self.identifier = identifier
        self.type_id = type_id
        self.value = value
        self.size = _UNIFORM_TYPE_TO_SIZE[type_id]


class _ConstantRegister:
    def __init__(self, index, is_relative=False):
        self.index = index
        self.is_relative = is_relative

    @property
    def type(self):
        """Causes this instance to be treated as a special token type."""
        return _REG_CONSTANT


def _merge_ops(
    ops: List[Tuple[vsh_encoder.Instruction, str]]
) -> Tuple[Optional[Tuple[vsh_encoder.Instruction, str]], str]:
    """Merges the given list of one or two instructions into a single instruction or error message."""
    if len(ops) == 1:
        return ops[0], ""

    if len(ops) != 2 or ops[0][0].opcode != ops[1][0].opcode:
        return None, "conflicting operations"

    if not ops[0][0].identical_inputs(ops[1][0]):
        return None, "operations have different inputs"

    # Reorder such that the temporary target comes last.
    op = ops[0][0]
    if op.dst_reg.targets_temporary:
        ops = [ops[1], ops[0]]

    # Ensure that there is one output and one temp.
    output_op = ops[0][0]
    if output_op.dst_reg.targets_temporary:
        return None, "operations both target temporary registers"

    temp_op = ops[1][0]
    if not temp_op.dst_reg.targets_temporary:
        return None, "operations both target output registers"

    output_op.secondary_dst_reg = temp_op.dst_reg
    merged_source = " + ".join([ops[0][1], ops[1][1]])

    return (output_op, merged_source), ""


def _distribute_mov_ops(
    mov_ops: List[Tuple[vsh_encoder.Instruction, str]], mac_ops: List, ilu_ops: List
) -> str:
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
        assert not (output_target or temp_target)
        return ""

    if temp_target:
        mac_ops.append(r1_target)
        assert not output_target
        return ""

    raise EncodingError("Unexpected MOV processing state")


def process_combined_operations(
    operations: List[Tuple[vsh_encoder.Instruction, str]], start_line: int = 0
) -> Tuple[vsh_encoder.Instruction, str]:
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
            if (
                opcode == vsh_encoder.Opcode.OPCODE_ADD
                or opcode == vsh_encoder.Opcode.OPCODE_SUB
            ):
                entry[0].swap_inputs_b_c()
            mac_ops.append(entry)

    num_mac = len(mac_ops)
    if num_mac > 1:
        merged, error = _merge_ops(mac_ops)
        if error:
            raise EncodingError(f"Conflicting MAC operations ({error}) at {start_line}")
        mac_ops = [merged]

    num_ilu = len(ilu_ops)
    if num_ilu > 1:
        merged, error = _merge_ops(ilu_ops)
        if error:
            raise EncodingError(f"Conflicting ILU operations ({error}) at {start_line}")
        ilu_ops = [merged]

    if mov_ops:
        error_message = _distribute_mov_ops(mov_ops, mac_ops, ilu_ops)
        if error_message:
            raise EncodingError(f"Invalid pairing ({error_message}) at {start_line}")

    if len(mac_ops) > 1:
        raise EncodingError(
            f"Invalid pairing (more than 2 MAC operations) at {start_line}"
        )
    if len(ilu_ops) > 1:
        raise EncodingError(
            f"Invalid pairing (more than 2 ILU operations) at {start_line}"
        )

    if mac_ops and ilu_ops:
        combined_op = mac_ops[0][0]
        combined_src = mac_ops[0][1]
        ilu_op = ilu_ops[0][0]
        ilu_src = ilu_ops[0][1]

        input_c = combined_op.src_reg[2]

        if input_c and input_c != ilu_op.src_reg[2]:
            raise EncodingError(
                f"Invalid instruction pairing (MAC operation uses input C which does not match ILU input)"
            )
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
        raise ValueError("Bad state, mac_ops and ilu_ops empty.")

    return combined


class EncodingVisitor(VshVisitor):
    """Visitor that generates a list of vsh instructions."""

    def __init__(self) -> None:
        super().__init__()
        self._uniforms = {}

    def visitStatement(self, ctx: VshParser.StatementContext):
        operations = self.visitChildren(ctx)
        if operations:
            return operations[0]
        return None

    def visitUniform_type(self, ctx: VshParser.Uniform_typeContext):
        assert len(ctx.children) == 1
        assert ctx.children[0].symbol.type in _UNIFORM_TYPE_TO_SIZE
        return ctx.children[0].symbol.type

    def visitUniform_declaration(self, ctx: VshParser.Uniform_declarationContext):
        uniform_type = self.visitChildren(ctx)[0]
        assert len(ctx.children) == 3
        identifier = ctx.children[0].symbol.text
        value = int(ctx.children[2].symbol.text)

        if identifier in self._uniforms:
            raise EncodingError(
                f"Duplicate definition of uniform {identifier} at line {ctx.start.line}"
            )
        self._uniforms[identifier] = _Uniform(identifier, uniform_type, value)
        return None

    def visitOperation(self, ctx: VshParser.OperationContext):
        instructions = self.visitChildren(ctx)
        assert len(instructions) == 1
        return instructions[0]

    def visitCombined_operation(self, ctx: VshParser.Combined_operationContext):
        operations = self.visitChildren(ctx)
        assert 2 <= len(operations) <= 4
        return process_combined_operations(operations, ctx.start.line)

    def visitOp_add(self, ctx: VshParser.Op_addContext):
        operands = self.visitChildren(ctx)
        assert len(operands) == 1
        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_ADD, *operands),
            f"add {self._prettify_operands(operands)}",
        )

    def visitOp_arl(self, ctx: VshParser.Op_arlContext):
        operands = self.visitChildren(ctx)
        assert len(operands) == 1
        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_ARL, *operands),
            f"add {self._prettify_operands(operands)}",
        )

    def visitOp_dp3(self, ctx: VshParser.Op_dp3Context):
        operands = self.visitChildren(ctx)
        assert len(operands) == 1
        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_DP3, *operands),
            f"dp3 {self._prettify_operands(operands)}",
        )

    def visitOp_dp4(self, ctx: VshParser.Op_dp4Context):
        operands = self.visitChildren(ctx)
        assert len(operands) == 1
        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_DP4, *operands),
            f"dp4 {self._prettify_operands(operands)}",
        )

    def visitOp_dph(self, ctx: VshParser.Op_dphContext):
        operands = self.visitChildren(ctx)
        assert len(operands) == 1
        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_DPH, *operands),
            f"dph {self._prettify_operands(operands)}",
        )

    def visitOp_dst(self, ctx: VshParser.Op_dstContext):
        operands = self.visitChildren(ctx)
        assert len(operands) == 1
        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_DST, *operands),
            f"dst {self._prettify_operands(operands)}",
        )

    def visitOp_expp(self, ctx: VshParser.Op_exppContext):
        operands = self.visitChildren(ctx)
        assert len(operands) == 1
        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_EXP, *operands),
            f"expp {self._prettify_operands(operands)}",
        )

    def visitOp_lit(self, ctx: VshParser.Op_litContext):
        operands = self.visitChildren(ctx)
        assert len(operands) == 1
        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_LIT, *operands),
            f"lit {self._prettify_operands(operands)}",
        )

    def visitOp_logp(self, ctx: VshParser.Op_logpContext):
        operands = self.visitChildren(ctx)
        assert len(operands) == 1
        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_LOG, *operands),
            f"logp {self._prettify_operands(operands)}",
        )

    def visitOp_mad(self, ctx: VshParser.Op_madContext):
        operands = self.visitChildren(ctx)
        assert len(operands) == 1
        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_MAD, *operands),
            f"mad {self._prettify_operands(operands)}",
        )

    def visitOp_max(self, ctx: VshParser.Op_maxContext):
        operands = self.visitChildren(ctx)
        assert len(operands) == 1
        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_MAX, *operands),
            f"max {self._prettify_operands(operands)}",
        )

    def visitOp_min(self, ctx: VshParser.Op_minContext):
        operands = self.visitChildren(ctx)
        assert len(operands) == 1
        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_MIN, *operands),
            f"min {self._prettify_operands(operands)}",
        )

    def visitOp_mov(self, ctx: VshParser.Op_movContext):
        operands = self.visitChildren(ctx)
        assert len(operands) == 1
        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_MOV, *operands),
            f"mov {self._prettify_operands(operands)}",
        )

    def visitOp_mul(self, ctx: VshParser.Op_mulContext):
        operands = self.visitChildren(ctx)
        assert len(operands) == 1
        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_MUL, *operands),
            f"mul {self._prettify_operands(operands)}",
        )

    def visitOp_rcc(self, ctx: VshParser.Op_rccContext):
        operands = self.visitChildren(ctx)
        assert len(operands) == 1
        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_RCC, *operands),
            f"rcc {self._prettify_operands(operands)}",
        )

    def visitOp_rcp(self, ctx: VshParser.Op_rcpContext):
        operands = self.visitChildren(ctx)
        assert len(operands) == 1
        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_RCP, *operands),
            f"rcp {self._prettify_operands(operands)}",
        )

    def visitOp_rsq(self, ctx: VshParser.Op_rsqContext):
        operands = self.visitChildren(ctx)
        assert len(operands) == 1
        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_RSQ, *operands),
            f"rsq {self._prettify_operands(operands)}",
        )

    def visitOp_sge(self, ctx: VshParser.Op_sgeContext):
        operands = self.visitChildren(ctx)
        assert len(operands) == 1
        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_SGE, *operands),
            f"sge {self._prettify_operands(operands)}",
        )

    def visitOp_slt(self, ctx: VshParser.Op_sltContext):
        operands = self.visitChildren(ctx)
        assert len(operands) == 1
        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_SLT, *operands),
            f"slt {self._prettify_operands(operands)}",
        )

    def visitOp_sub(self, ctx: VshParser.Op_subContext):
        operands = self.visitChildren(ctx)
        assert len(operands) == 1
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
            assert len(operands) == 1
            target = operands[0]
            assert target.type == _REG_CONSTANT
        else:
            target = ctx.children[0].symbol
        mask = None
        if len(ctx.children) > 1:
            mask = ctx.children[1].symbol
        return self._process_output(target, mask)

    def visitP_input_raw(self, ctx: VshParser.P_input_rawContext):
        subtree = self.visitChildren(ctx)
        if subtree:
            source = subtree[0]
        else:
            source = ctx.children[0].symbol
        swizzle = None
        if len(ctx.children) > 1:
            swizzle = ctx.children[1].symbol
        return self._process_input(source, swizzle)

    def visitP_input_negated(self, ctx: VshParser.P_input_negatedContext):
        contents = self.visitChildren(ctx)
        assert len(contents) == 1
        src_reg = contents[0]
        src_reg.set_negated()
        return src_reg

    def visitP_input(self, ctx: VshParser.P_inputContext):
        contents = self.visitChildren(ctx)
        return contents[0]

    def visitReg_const(self, ctx: VshParser.Reg_constContext):
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
                raise EncodingError(f"Failed to parse relative constant {reg.text}")
            register = int(match.group(1))
            return _ConstantRegister(register, True)
        if reg.type == VshLexer.REG_Cx_RELATIVE_A_SECOND:
            match = _RELATIVE_CONSTANT_A_SECOND_RE.match(reg.text)
            if not match:
                raise EncodingError(f"Failed to parse relative constant {reg.text}")
            register = int(match.group(1))
            return _ConstantRegister(register, True)

        raise EncodingError(
            f"TODO: Implement unhandled const register format {reg.text}"
        )

    def visitUniform_const(self, ctx: VshParser.Uniform_constContext):
        name = ctx.children[0].symbol.text
        uniform: Optional[_Uniform] = self._uniforms.get(name)
        if not uniform:
            raise EncodingError(
                f"Undefined uniform {name} used at line {ctx.start.line}"
            )

        offset = 0
        if len(ctx.children) > 1:
            offset = int(ctx.children[2].symbol.text)

        if offset >= uniform.size:
            raise EncodingError(
                f"Uniform offset out of range (max is {uniform.size - 1}) at line {ctx.start.line}"
            )

        return _ConstantRegister(uniform.value + offset)

    @staticmethod
    def _process_destination_mask(mask):
        if not mask:
            return vsh_encoder.WRITEMASK_XYZW

        return _DESTINATION_MASK_LOOKUP[mask.text.lower()]

    def _process_output(self, target, mask):
        mask = self._process_destination_mask(mask)

        if target.type == VshLexer.REG_Rx:
            register = int(target.text[1:])
            return vsh_encoder.DestinationRegister(
                vsh_encoder.RegisterFile.PROGRAM_TEMPORARY, register, mask
            )

        if target.type == VshLexer.REG_OUTPUT:
            register = _NAME_TO_DESTINATION_REGISTER_MAP[target.text]
            return vsh_encoder.DestinationRegister(
                vsh_encoder.RegisterFile.PROGRAM_OUTPUT, register, mask
            )

        if target.type == VshLexer.REG_A0:
            return vsh_encoder.DestinationRegister(
                vsh_encoder.RegisterFile.PROGRAM_ADDRESS,
                vsh_encoder.OutputRegisters.REG_A0,
                mask,
            )

        if target.type == _REG_CONSTANT:
            if target.is_relative:
                # TODO: Check if this is supported in the HW.
                # Then implement or update grammar to disallow.
                raise EncodingError(f"Unsupported write to relative constant register.")
            return vsh_encoder.DestinationRegister(
                vsh_encoder.RegisterFile.PROGRAM_ENV_PARAM,
                target.index,
                mask,
            )

        raise EncodingError(
            f"Unsupported output target '{target.text}' at {target.line}:{target.column}"
        )

    @staticmethod
    def _process_source_swizzle(swizzle):
        if not swizzle:
            return vsh_encoder.SWIZZLE_XYZW

        # ".zzzz"
        swizzle_elements = swizzle.text[1:].lower()
        elements = [_SWIZZLE_LOOKUP[c] for c in swizzle_elements]
        return vsh_encoder.make_swizzle(*elements)

    def _process_input(self, source, swizzle):
        swizzle = self._process_source_swizzle(swizzle)

        if source.type == VshLexer.REG_Rx or source.type == VshLexer.REG_R12:
            register = int(source.text[1:])
            return vsh_encoder.SourceRegister(
                vsh_encoder.RegisterFile.PROGRAM_TEMPORARY, register, swizzle
            )

        if source.type == VshLexer.REG_INPUT:
            register = _SOURCE_REGISTER_LOOKUP[source.text.lower()]
            return vsh_encoder.SourceRegister(
                vsh_encoder.RegisterFile.PROGRAM_INPUT, register, swizzle
            )

        if source.type == _REG_CONSTANT:
            return vsh_encoder.SourceRegister(
                vsh_encoder.RegisterFile.PROGRAM_ENV_PARAM,
                source.index,
                swizzle,
                source.is_relative,
            )

        raise EncodingError(
            f"Unsupported input register '{source.text}' at {source.line}:{source.column}"
        )

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

        if (
            register.file == vsh_encoder.RegisterFile.PROGRAM_OUTPUT
            or register.file == vsh_encoder.RegisterFile.PROGRAM_ADDRESS
        ):
            name = vsh_encoder_defs.DESTINATION_REGISTER_TO_NAME_MAP[register.index]
            return f"{name}{mask}"

        if register.file == vsh_encoder.RegisterFile.PROGRAM_ENV_PARAM:
            return f"c[{register.index}]{mask}"

        raise EncodingError("TODO: Implement destination register prettification.")

    @staticmethod
    def _prettify_source(register: vsh_encoder.SourceRegister) -> str:
        swizzle = vsh_instruction.get_swizzle_name(register.swizzle)
        if swizzle == "xyzw":
            swizzle = ""
        else:
            swizzle = f".{swizzle}"

        prefix = ""
        if register.negate:
            prefix = "-"

        if register.file == vsh_encoder.RegisterFile.PROGRAM_TEMPORARY:
            return f"{prefix}r{register.index}{swizzle}"

        if register.file == vsh_encoder.RegisterFile.PROGRAM_ENV_PARAM:
            return f"{prefix}c{register.index}{swizzle}"

        if register.file == vsh_encoder.RegisterFile.PROGRAM_INPUT:
            name = _SOURCE_REGISTER_TO_NAME_MAP[register.index]
            return f"{prefix}{name}{swizzle}"

        raise EncodingError("TODO: Implement destination register prettification.")

    def _prettify_operands(self, operands) -> str:

        num_operands = len(operands)
        if not num_operands:
            return ""

        elements = [self._prettify_destination(operands[0])]
        elements.extend([self._prettify_source(src) for src in operands[1:]])

        return ", ".join(elements)
