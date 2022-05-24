"""Provides an ANTLR visitor that generates vsh instructions."""
import re

from build.grammar.VshLexer import VshLexer
from build.grammar.VshParser import VshParser
from build.grammar.VshVisitor import VshVisitor

from . import vsh_encoder

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

_DESTINATION_REGISTER_TO_NAME_MAP = {
    vsh_encoder.OutputRegisters.REG_POS: "oPos",
    vsh_encoder.OutputRegisters.REG_DIFFUSE: "oDiffuse",
    vsh_encoder.OutputRegisters.REG_SPECULAR: "oSpecular",
    vsh_encoder.OutputRegisters.REG_FOG_COORD: "oFog",
    vsh_encoder.OutputRegisters.REG_POINT_SIZE: "oPts",
    vsh_encoder.OutputRegisters.REG_BACK_DIFFUSE: "oBackDiffuse",
    vsh_encoder.OutputRegisters.REG_BACK_SPECULAR: "oBackSpecular",
    vsh_encoder.OutputRegisters.REG_TEX0: "oTex0",
    vsh_encoder.OutputRegisters.REG_TEX1: "oTex1",
    vsh_encoder.OutputRegisters.REG_TEX2: "oTex2",
    vsh_encoder.OutputRegisters.REG_TEX3: "oTex3",
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


class EncodingVisitor(VshVisitor):
    """Visitor that generates a list of vsh instructions."""

    class _ConstantRegister:
        def __init__(self, index, is_relative=False):
            self.index = index
            self.is_relative = is_relative

        @property
        def type(self):
            return _REG_CONSTANT

    def visitStatement(self, ctx: VshParser.StatementContext):
        operations = self.visitChildren(ctx)
        if operations:
            return operations[0]
        return None

    def visitOperation(self, ctx: VshParser.OperationContext):
        instructions = self.visitChildren(ctx)
        assert len(instructions) == 1
        return instructions[0]

    def visitCombined_operation(self, ctx: VshParser.Combined_operationContext):
        operations = self.visitChildren(ctx)
        assert len(operations) == 2

        a, a_src = operations[0]
        b, b_src = operations[1]
        a_ilu = a.opcode.is_ilu()
        b_ilu = b.opcode.is_ilu()

        # Detect ILU mov instruction pairing (a mov + a MAC instruction implies ILU mov)
        if not (a_ilu or b_ilu):
            if a.opcode == vsh_encoder.Opcode.OPCODE_MOV:
                a_ilu = True
            if b.opcode == vsh_encoder.Opcode.OPCODE_MOV:
                b_ilu = True

        if a_ilu and b_ilu:
            raise Exception(
                f"Invalid instruction pairing (both ILU) at {ctx.start.line}"
            )
        if not (a_ilu or b_ilu):
            raise Exception(
                f"Invalid instruction pairing (both MAC) at {ctx.start.line}"
            )

        if a_ilu:
            temp = a
            a = b
            b = temp
            temp = a_src
            a_src = b_src
            b_src = temp

        ilu_dst: vsh_encoder.DestinationRegister = b.dst_reg
        mac_dst: vsh_encoder.DestinationRegister = a.dst_reg
        if (
            mac_dst.file == vsh_encoder.RegisterFile.PROGRAM_TEMPORARY
            and mac_dst.index == 1
        ):
            print(
                f"Warning: MAC instruction writing to R1 in MAC+ILU pairing at {ctx.start.line} will be ignored."
            )

        return (
            vsh_encoder.Instruction(
                a.opcode,
                a.dst_reg,
                a.src_reg[0],
                a.src_reg[1],
                b.src_reg[0],
                b.opcode,
                ilu_dst,
            ),
            f"{a_src} + {b_src}",
        )

    def visitOp_add(self, ctx: VshParser.Op_addContext):
        operands = self.visitChildren(ctx)
        assert len(operands) == 1
        operands = operands[0]
        return (
            vsh_encoder.Instruction(vsh_encoder.Opcode.OPCODE_ADD, *operands),
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

    def visitP_output(self, ctx: VshParser.P_outputContext):
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
            return self._ConstantRegister(register)
        if reg.type == VshLexer.REG_Cx_BRACKETED:
            register = int(reg.text[2:-1])
            return self._ConstantRegister(register)
        if reg.type == VshLexer.REG_Cx_RELATIVE_A_FIRST:
            match = _RELATIVE_CONSTANT_A_FIRST_RE.match(reg.text)
            if not match:
                raise Exception(f"Failed to parse relative constant {reg.text}")
            register = int(match.group(1))
            return self._ConstantRegister(register, True)
        if reg.type == VshLexer.REG_Cx_RELATIVE_A_SECOND:
            match = _RELATIVE_CONSTANT_A_SECOND_RE.match(reg.text)
            if not match:
                raise Exception(f"Failed to parse relative constant {reg.text}")
            register = int(match.group(1))
            return self._ConstantRegister(register, True)

        raise Exception(f"TODO: Implement unhandled const register format {reg.text}")

    def _process_destination_mask(self, mask):
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

        raise Exception(
            f"Unsupported output target '{target.text}' at {target.line}:{target.column}"
        )

    def _process_source_swizzle(self, swizzle):
        if not swizzle:
            return vsh_encoder.SWIZZLE_XYZW

        # ".zzzz"
        swizzle_elements = swizzle.text[1:].lower()
        elements = [_SWIZZLE_LOOKUP[c] for c in swizzle_elements]
        return vsh_encoder.make_swizzle(*elements)

    def _process_input(self, source, swizzle):
        swizzle = self._process_source_swizzle(swizzle)

        if source.type == VshLexer.REG_Rx:
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
                vsh_encoder.RegisterFile.PROGRAM_ENV_PARAM, source.index, swizzle
            )

        if source.type == VshLexer.REG_A0:
            return vsh_encoder.SourceRegister(
                vsh_encoder.RegisterFile.PROGRAM_ADDRESS,
                0,
                vsh_encoder.make_swizzle(vsh_encoder.SWIZZLE_X),
            )

        raise Exception(
            f"Unsupported input register '{source.text}' at {source.line}:{source.column}"
        )

    def aggregateResult(self, aggregate, nextResult):
        if nextResult is None:
            return aggregate

        if aggregate is None:
            aggregate = []
        aggregate.append(nextResult)
        return aggregate

    def _prettify_destination(self, register: vsh_encoder.DestinationRegister) -> str:
        mask = vsh_encoder.get_writemask_name(register.write_mask)

        if register.file == vsh_encoder.RegisterFile.PROGRAM_TEMPORARY:
            return f"r{register.index}{mask}"

        if register.file == vsh_encoder.RegisterFile.PROGRAM_OUTPUT:
            name = _DESTINATION_REGISTER_TO_NAME_MAP[register.index]
            return f"{name}{mask}"

        raise Exception("TODO: Implement destination register prettification.")

    def _prettify_source(self, register: vsh_encoder.SourceRegister) -> str:
        swizzle = vsh_encoder.get_swizzle_name(register.swizzle)
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

        raise Exception("TODO: Implement destination register prettification.")

    def _prettify_operands(self, operands) -> str:

        num_operands = len(operands)
        if not num_operands:
            return ""

        elements = [self._prettify_destination(operands[0])]
        elements.extend([self._prettify_source(src) for src in operands[1:]])

        return ", ".join(elements)
