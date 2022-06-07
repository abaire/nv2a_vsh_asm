"""Tests for vsh_encoder."""

# pylint: disable=missing-function-docstring
# pylint: disable=too-many-public-methods
# pylint: disable=unused-wildcard-import
# pylint: disable=wildcard-import
# pylint: disable=wrong-import-order

from typing import List
import unittest

from nv2avsh.nv2a_vsh_asm import encoding_visitor
from nv2avsh.nv2a_vsh_asm.vsh_encoder import *
from nv2avsh.nv2a_vsh_asm.vsh_instruction import vsh_diff_instructions


class VSHEncoderTestCase(unittest.TestCase):
    """Tests for vsh_encoder."""

    def test_empty(self):
        results = encode([])
        self.assertEqual([], results)

    def test_incompatible_constant_inputs_fails(self):
        # ADD oPos, c[12], c[13]
        dst = DestinationRegister(RegisterFile.PROGRAM_OUTPUT, OutputRegisters.REG_POS)
        src_a = SourceRegister(RegisterFile.PROGRAM_ENV_PARAM, 12)
        src_b = SourceRegister(RegisterFile.PROGRAM_ENV_PARAM, 13)
        program = [Instruction(Opcode.OPCODE_ADD, dst, src_a=src_a, src_b=src_b)]

        with self.assertRaises(encoding_visitor.EncodingError) as err:
            encode(program)
        self.assertEqual(
            "Operation reads from more than one C register (c[12] and c[13])",
            str(err.exception),
        )

    def test_compatible_constant_inputs(self):
        # ADD oPos, c[12], c[12]
        dst = DestinationRegister(RegisterFile.PROGRAM_OUTPUT, OutputRegisters.REG_POS)
        src_a = SourceRegister(RegisterFile.PROGRAM_ENV_PARAM, 12)
        src_b = src_a
        program = [Instruction(Opcode.OPCODE_ADD, dst, src_a=src_a, src_b=src_b)]

        results = encode(program)
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x0061801B, 0x0C36106C, 0x3070F800], results[0])

    def test_mov_out_in_unswizzled(self):
        program = []

        # MOV oD0.xyzw, v3
        dst = DestinationRegister(
            RegisterFile.PROGRAM_OUTPUT, OutputRegisters.REG_DIFFUSE
        )
        src = SourceRegister(RegisterFile.PROGRAM_INPUT, InputRegisters.REG_DIFFUSE)
        program.append(Instruction(Opcode.OPCODE_MOV, output=dst, src_a=src))

        results = encode(program)
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x0020061B, 0x0836106C, 0x2070F818], results[0])

    def test_mov_out_in_swizzled(self):
        program = []

        # MOV(oT0.xy, v0.zw);
        dst = DestinationRegister(
            RegisterFile.PROGRAM_OUTPUT, OutputRegisters.REG_TEX0, WRITEMASK_XY
        )
        src = SourceRegister(
            RegisterFile.PROGRAM_INPUT,
            InputRegisters.V0,
            make_swizzle(SWIZZLE_Z, SWIZZLE_W),
        )
        program.append(Instruction(Opcode.OPCODE_MOV, output=dst, src_a=src))

        results = encode(program)
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x002000BF, 0x0836106C, 0x2070C848], results[0])

    def test_mov_out_temp_swizzled(self):
        program = []

        # MOV oPos.xy, R0.xy
        dst = DestinationRegister(
            RegisterFile.PROGRAM_OUTPUT, OutputRegisters.REG_POS, WRITEMASK_XY
        )
        src = SourceRegister(
            RegisterFile.PROGRAM_TEMPORARY, 0, make_swizzle(SWIZZLE_X, SWIZZLE_Y)
        )
        program.append(Instruction(Opcode.OPCODE_MOV, output=dst, src_a=src))

        results = encode(program)
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x00200015, 0x0436106C, 0x2070C800], results[0])

    def test_rcp_out_in_swizzled(self):
        program = []
        # RCP oFog.xyzw, v0.w
        dst = DestinationRegister(
            RegisterFile.PROGRAM_OUTPUT, OutputRegisters.REG_FOG_COORD
        )
        src = SourceRegister(
            RegisterFile.PROGRAM_INPUT, InputRegisters.V0, make_swizzle(SWIZZLE_W)
        )
        program.append(Instruction(Opcode.OPCODE_RCP, output=dst, src_a=src))

        results = encode(program)
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)

        self._assert_vsh([0x00000000, 0x0400001B, 0x083613FC, 0x2070F82C], results[0])

    # ORB mismatch, expect 0, got 1
    # def test_min_temp_temp_const_inverse_swizzle(self):
    #     program = []
    #
    #     # MIN(R0,xyzw, R0.x, c[108].wzyx);
    #     dst = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 0, WRITEMASK_XYZW)
    #     src_a = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, 0,
    #                           make_swizzle(SWIZZLE_X))
    #     src_b = SourceRegister(RegisterFile.PROGRAM_ENV_PARAM, 108 - 96,
    #                         make_swizzle(SWIZZLE_W, SWIZZLE_Z, SWIZZLE_Y, SWIZZLE_X))
    #     program.append(Instruction(Opcode.OPCODE_MIN, dst, src_a, src_b))
    #
    #     results = encode(program)
    #     self._assert_final_marker(results)
    #     self.assertEqual(len(results), 2)
    #     self._assert_vsh([0x00000000, 0x012D8000, 0x05C8186C, 0x2F0007F8], results[0])

    def test_mul_temp_in_const_swizzled(self):
        program = []

        # MUL R0.x, v0.x, c96.x // Ignore rest of line
        dst = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 0, WRITEMASK_X)
        src_a = SourceRegister(
            RegisterFile.PROGRAM_INPUT, InputRegisters.V0, make_swizzle(SWIZZLE_X)
        )
        src_b = SourceRegister(
            RegisterFile.PROGRAM_ENV_PARAM, 96, make_swizzle(SWIZZLE_X)
        )
        program.append(Instruction(Opcode.OPCODE_MUL, dst, src_a=src_a, src_b=src_b))

        results = encode(program)
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x004C0000, 0x0800186C, 0x28000FF8], results[0])

    def test_add_temp_temp_const_swizzle(self):
        program = []

        # ADD R0.y, R0.y, c[97].w
        dst = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 0, WRITEMASK_Y)
        src_a = SourceRegister(
            RegisterFile.PROGRAM_TEMPORARY, 0, make_swizzle(SWIZZLE_Y)
        )
        src_b = SourceRegister(
            RegisterFile.PROGRAM_ENV_PARAM, 97, make_swizzle(SWIZZLE_W)
        )
        program.append(Instruction(Opcode.OPCODE_ADD, dst, src_a=src_a, src_b=src_b))

        results = encode(program)
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x006C2055, 0x043613FC, 0x34000FF8], results[0])

    def test_dp4_out_in_const(self):
        program = []

        # DP4(oPos,x, v0, c[96]);
        dst = DestinationRegister(
            RegisterFile.PROGRAM_OUTPUT, OutputRegisters.REG_POS, WRITEMASK_X
        )
        src_a = SourceRegister(RegisterFile.PROGRAM_INPUT, InputRegisters.V0)
        src_b = SourceRegister(RegisterFile.PROGRAM_ENV_PARAM, 96)
        program.append(Instruction(Opcode.OPCODE_DP4, dst, src_a=src_a, src_b=src_b))

        results = encode(program)
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x00EC001B, 0x0836186C, 0x20708800], results[0])

    def test_mad_temp_in_temp_const(self):
        program = []

        # MAD(R0,x, v0.y, c[96].y, R0.x);
        dst = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 0, WRITEMASK_X)
        src_a = SourceRegister(
            RegisterFile.PROGRAM_INPUT, InputRegisters.V0, make_swizzle(SWIZZLE_Y)
        )
        src_b = SourceRegister(
            RegisterFile.PROGRAM_ENV_PARAM, 96, make_swizzle(SWIZZLE_Y)
        )
        src_c = SourceRegister(
            RegisterFile.PROGRAM_TEMPORARY, 0, make_swizzle(SWIZZLE_X)
        )
        program.append(
            Instruction(Opcode.OPCODE_MAD, dst, src_a=src_a, src_b=src_b, src_c=src_c)
        )

        results = encode(program)
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x008C0055, 0x08AA1800, 0x18000FF8], results[0])

    def test_mac_mov_ilu_rcp(self):
        program = []

        # MOV(oD0,xyzw, v3);
        # + RCP(R1,w, R1.w);
        dst = DestinationRegister(
            RegisterFile.PROGRAM_OUTPUT, OutputRegisters.REG_DIFFUSE, WRITEMASK_XYZW
        )
        ilu_dst = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 1, WRITEMASK_W)
        src_a = SourceRegister(RegisterFile.PROGRAM_INPUT, InputRegisters.V3)
        src_c = SourceRegister(
            RegisterFile.PROGRAM_TEMPORARY, 1, make_swizzle(SWIZZLE_W)
        )

        ins = Instruction(
            Opcode.OPCODE_MOV,
            dst,
            src_a=src_a,
            src_b=None,
            src_c=src_c,
            paired_ilu_opcode=Opcode.OPCODE_RCP,
            paired_ilu_dst_reg=ilu_dst,
        )

        program.append(ins)

        results = encode(program)
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x0420061B, 0x083613FC, 0x5011F818], results[0])

    def test_mac_mov_ilu_rcc(self):
        program = []

        # MOV(oT1,xyzw, v3);
        # RCC(R1,x, R12.w);
        dst = DestinationRegister(RegisterFile.PROGRAM_OUTPUT, OutputRegisters.REG_TEX1)
        ilu_dst = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 1, WRITEMASK_X)
        src_a = SourceRegister(RegisterFile.PROGRAM_INPUT, InputRegisters.V3)
        src_c = SourceRegister(
            RegisterFile.PROGRAM_TEMPORARY, 12, make_swizzle(SWIZZLE_W)
        )

        ins = Instruction(
            Opcode.OPCODE_MOV,
            dst,
            src_a=src_a,
            src_b=None,
            src_c=src_c,
            paired_ilu_opcode=Opcode.OPCODE_RCC,
            paired_ilu_dst_reg=ilu_dst,
        )

        program.append(ins)

        results = encode(program)
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x0620061B, 0x083613FF, 0x1018F850], results[0])

    def test_mac_mul_ilu_rcc(self):
        program = []

        # MUL(oD0,xyzw, v1, c[188]);
        # RCC(R1,x, R12.w);
        dst = DestinationRegister(
            RegisterFile.PROGRAM_OUTPUT, OutputRegisters.REG_DIFFUSE
        )
        ilu_dst = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 1, WRITEMASK_X)
        src_a = SourceRegister(RegisterFile.PROGRAM_INPUT, InputRegisters.V1)
        src_b = SourceRegister(RegisterFile.PROGRAM_ENV_PARAM, 188)
        src_c = SourceRegister(
            RegisterFile.PROGRAM_TEMPORARY, 12, make_swizzle(SWIZZLE_W)
        )

        ins = Instruction(
            Opcode.OPCODE_MUL,
            dst,
            src_a=src_a,
            src_b=src_b,
            src_c=src_c,
            paired_ilu_opcode=Opcode.OPCODE_RCC,
            paired_ilu_dst_reg=ilu_dst,
        )

        program.append(ins)

        results = encode(program)
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x0657821B, 0x08361BFF, 0x1018F818], results[0])

    def test_mac_mul_ilu_mov(self):
        program = []

        # MUL R2.xyzw, R1, c[0]
        # + MOV oD1.xyzw, v4
        dst = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 2)
        ilu_dst = DestinationRegister(
            RegisterFile.PROGRAM_OUTPUT, OutputRegisters.REG_SPECULAR
        )
        src_a = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, 1)
        src_b = SourceRegister(RegisterFile.PROGRAM_ENV_PARAM, 0)
        src_c = SourceRegister(RegisterFile.PROGRAM_INPUT, InputRegisters.V4)

        ins = Instruction(
            Opcode.OPCODE_MUL,
            dst,
            src_a=src_a,
            src_b=src_b,
            src_c=src_c,
            paired_ilu_opcode=Opcode.OPCODE_MOV,
            paired_ilu_dst_reg=ilu_dst,
        )

        program.append(ins)

        results = encode(program)
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x0240081B, 0x1436186C, 0x2F20F824], results[0])

    def test_mac_mov_ilu_mov(self):
        program = []

        # MOV R5.xyz, R4
        # + MOV oT0.xy, v1
        dst = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 5, WRITEMASK_XYZ)
        ilu_dst = DestinationRegister(
            RegisterFile.PROGRAM_OUTPUT, OutputRegisters.REG_TEX0, WRITEMASK_XY
        )
        src_a = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, 4)
        src_b = None
        src_c = SourceRegister(RegisterFile.PROGRAM_INPUT, InputRegisters.V1)

        ins = Instruction(
            Opcode.OPCODE_MOV,
            dst,
            src_a=src_a,
            src_b=src_b,
            src_c=src_c,
            paired_ilu_opcode=Opcode.OPCODE_MOV,
            paired_ilu_dst_reg=ilu_dst,
        )

        program.append(ins)

        results = encode(program)
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x0220021B, 0x4436106C, 0x2E50C84C], results[0])

    def test_mac_mov_temp_const_ilu_mov_out_in(self):
        program = []

        # MOV R8.xyz, c27
        # + MOV oD0.w, v4.z
        dst = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 8, WRITEMASK_XYZ)
        ilu_dst = DestinationRegister(
            RegisterFile.PROGRAM_OUTPUT, OutputRegisters.REG_DIFFUSE, WRITEMASK_W
        )
        src_a = SourceRegister(RegisterFile.PROGRAM_ENV_PARAM, 27)
        src_b = None
        src_c = SourceRegister(
            RegisterFile.PROGRAM_INPUT, InputRegisters.V4, make_swizzle(SWIZZLE_Z)
        )

        ins = Instruction(
            Opcode.OPCODE_MOV,
            dst,
            src_a=src_a,
            src_b=src_b,
            src_c=src_c,
            paired_ilu_opcode=Opcode.OPCODE_MOV,
            paired_ilu_dst_reg=ilu_dst,
        )

        program.append(ins)

        results = encode(program)
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x0223681B, 0x0C3612A8, 0x2E80181C], results[0])

    def test_mac_dp3_ilu_mov(self):
        program = []

        # DP3 R7,w, R6, R6
        # + MOV oT3.xyz, R5
        dst = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 7, WRITEMASK_W)
        ilu_dst = DestinationRegister(
            RegisterFile.PROGRAM_OUTPUT, OutputRegisters.REG_TEX3, WRITEMASK_XYZ
        )
        src_a = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, 6)
        src_b = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, 6)
        src_c = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, 5)

        ins = Instruction(
            Opcode.OPCODE_DP3,
            dst,
            src_a=src_a,
            src_b=src_b,
            src_c=src_c,
            paired_ilu_opcode=Opcode.OPCODE_MOV,
            paired_ilu_dst_reg=ilu_dst,
        )

        program.append(ins)

        results = encode(program)
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x02A0001B, 0x6436C86D, 0x5170E864], results[0])

    def test_add_temp_const_neg_temp(self):
        program = []
        # ADD R6.xyz, c17, -R10
        dst = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 6, WRITEMASK_XYZ)
        src_a = SourceRegister(RegisterFile.PROGRAM_ENV_PARAM, 17)
        src_b = SourceRegister(
            RegisterFile.PROGRAM_TEMPORARY, 10, SWIZZLE_XYZW, 0, True
        )
        program.append(Instruction(Opcode.OPCODE_ADD, dst, src_a=src_a, src_b=src_b))

        results = encode(program)
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)

        self._assert_vsh([0x00000000, 0x0062201B, 0x0C36146E, 0x9E600FF8], results[0])

    def test_mad_temp_temp_const_const_neg(self):
        program = []

        # MAD R0.z, R0.z, c[117].z, -c[117].w
        dst = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 0, WRITEMASK_Z)

        src_a = SourceRegister(
            RegisterFile.PROGRAM_TEMPORARY, 0, make_swizzle(SWIZZLE_Z)
        )
        src_b = SourceRegister(
            RegisterFile.PROGRAM_ENV_PARAM, 117, make_swizzle(SWIZZLE_Z)
        )
        src_c = SourceRegister(
            RegisterFile.PROGRAM_ENV_PARAM, 117, make_swizzle(SWIZZLE_W), 0, True
        )
        program.append(
            Instruction(Opcode.OPCODE_MAD, dst, src_a=src_a, src_b=src_b, src_c=src_c)
        )

        results = encode(program)
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x008EA0AA, 0x05541FFC, 0x32000FF8], results[0])
        # xemu decompiles this to the same instruction
        # self._assert_vsh([0x00000000, 0x008EA0AA, 0x0554BFFD, 0x72000000], results[0])

    def test_mac_arl_ilu_mov(self):
        # ARL A0, R2
        # + MOV oD0.w, v4.z
        # // [0x00000000, 0x03A0081B, 0x243612A8, 0x2070181C]
        pass

    def test_mac_mul_neg_ilu_mov(self):
        # MUL R7.w, -R6.x, c14.z
        # + MOV oT3.xyz, R5
        # // [0x00000000, 0x0241C100, 0x6554186D, 0x5170E864]
        pass

    def _assert_final_marker(self, results):
        self.assertEqual([0, 0, 0, 1], results[-1])

    def _assert_vsh(self, expected: List[int], actual: List[int]):
        diff = vsh_diff_instructions(expected, actual)
        if diff:
            raise self.failureException(diff)


class VSHEncodingVisitorMergeOpsTestCase(unittest.TestCase):
    """Tests the encoding_visitor._merge_mov_ops method."""

    def test_merge_mov_ops_single(self):
        operations = []

        # MOV R1, R0
        dst_ilu_temp = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 1)
        src_a = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, 0)
        operations.append(
            (Instruction(Opcode.OPCODE_MOV, dst_ilu_temp, src_a=src_a), "MOV R1, R0")
        )

        merged, error = encoding_visitor._merge_ops(operations)
        self.assertEqual("", error)
        self.assertEqual(operations[0], merged)

    def test_merge_mov_ops_valid_pair(self):
        operations = []

        # MOV R1, R0
        dst_ilu_temp = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 1)
        src_a = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, 0)
        operations.append(
            (Instruction(Opcode.OPCODE_MOV, dst_ilu_temp, src_a=src_a), "MOV R1, R0")
        )

        # MOV oPos, R0
        dst_ilu_output = DestinationRegister(
            RegisterFile.PROGRAM_OUTPUT, OutputRegisters.REG_POS
        )
        operations.append(
            (
                Instruction(Opcode.OPCODE_MOV, dst_ilu_output, src_a=src_a),
                "MOV oPos, R0",
            )
        )

        merged, error = encoding_visitor._merge_ops(operations)
        self.assertEqual("", error)

        expected_op = Instruction(
            Opcode.OPCODE_MOV,
            dst_ilu_output,
            secondary_output=dst_ilu_temp,
            src_a=src_a,
        )
        self.assertEqual(expected_op, merged[0])

        self.assertEqual("MOV oPos, R0 + MOV R1, R0", merged[1])

    def test_merge_mov_ops_invalid_double_output(self):
        operations = []

        dst_ilu_temp = DestinationRegister(
            RegisterFile.PROGRAM_OUTPUT, OutputRegisters.REG_DIFFUSE
        )
        src_a = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, 0)
        operations.append(
            (Instruction(Opcode.OPCODE_MOV, dst_ilu_temp, src_a=src_a), "MOV oD0, R0")
        )

        dst_ilu_output = DestinationRegister(
            RegisterFile.PROGRAM_OUTPUT, OutputRegisters.REG_POS
        )
        operations.append(
            (
                Instruction(Opcode.OPCODE_MOV, dst_ilu_output, src_a=src_a),
                "MOV oPos, R0",
            )
        )

        merged, error = encoding_visitor._merge_ops(operations)
        self.assertEqual("operations both target output registers", error)

    def test_merge_mov_ops_invalid_double_temporary(self):
        operations = []

        dst = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 1)
        src_a = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, 0)
        operations.append(
            (Instruction(Opcode.OPCODE_MOV, dst, src_a=src_a), "MOV R1, R0")
        )

        dst = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 10)
        operations.append(
            (
                Instruction(Opcode.OPCODE_MOV, dst, src_a=src_a),
                "MOV R10, R0",
            )
        )

        merged, error = encoding_visitor._merge_ops(operations)
        self.assertEqual("operations both target temporary registers", error)


class VSHEncodingVisitorDistributeMovOpsTestCase(unittest.TestCase):
    """Tests the encoding_visitor._distribute_mov_ops method."""

    def test_distribute_three_movs_non_overlapping_inputs_fails(self):
        operations = []

        # MOV R1, R0
        dst = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 1)
        src_a = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, 0)
        operations.append(
            (Instruction(Opcode.OPCODE_MOV, dst, src_a=src_a), "MOV R1, R0")
        )

        # MOV oPos, R2
        dst = DestinationRegister(RegisterFile.PROGRAM_OUTPUT, OutputRegisters.REG_POS)
        src_a = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, 2)
        operations.append(
            (
                Instruction(Opcode.OPCODE_MOV, dst, src_a=src_a),
                "MOV oPos, R2",
            )
        )

        # MOV R7, R3
        dst = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 7)
        src_a = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, 3)
        operations.append(
            (Instruction(Opcode.OPCODE_MOV, dst, src_a=src_a), "MOV R7, R3")
        )

        mac_ops = []
        ilu_ops = []
        error = encoding_visitor._distribute_mov_ops(operations, mac_ops, ilu_ops)
        self.assertEqual("more than 2 distinct sets of inputs", error)

    def test_distribute_two_movs_targeting_outputs_fails(self):
        operations = []

        # MOV oPos, R2
        dst = DestinationRegister(RegisterFile.PROGRAM_OUTPUT, OutputRegisters.REG_POS)
        src_a = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, 2)
        operations.append(
            (
                Instruction(Opcode.OPCODE_MOV, dst, src_a=src_a),
                "MOV oPos, R2",
            )
        )

        # MOV oD0, R3
        dst = DestinationRegister(
            RegisterFile.PROGRAM_OUTPUT, OutputRegisters.REG_DIFFUSE
        )
        src_a = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, 3)
        operations.append(
            (Instruction(Opcode.OPCODE_MOV, dst, src_a=src_a), "MOV oD0, R3")
        )

        mac_ops = []
        ilu_ops = []
        error = encoding_visitor._distribute_mov_ops(operations, mac_ops, ilu_ops)
        self.assertEqual("more than 1 MOV targets an output register", error)

    def test_distribute_two_movs_targeting_non_r1_temporary_regs_fails(self):
        operations = []

        # MOV R3, R2
        dst = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 3)
        src_a = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, 2)
        operations.append(
            (
                Instruction(Opcode.OPCODE_MOV, dst, src_a=src_a),
                "MOV R3, R2",
            )
        )

        # MOV R7, R3
        dst = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 7)
        src_a = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, 3)
        operations.append(
            (Instruction(Opcode.OPCODE_MOV, dst, src_a=src_a), "MOV R7, R3")
        )

        mac_ops = []
        ilu_ops = []
        error = encoding_visitor._distribute_mov_ops(operations, mac_ops, ilu_ops)
        self.assertEqual("more than 1 MOV targets a non-R1 temporary register", error)

    def test_distribute_two_movs_r1_temporary_regs_fails(self):
        operations = []

        # MOV R1, R2
        dst = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 1)
        src_a = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, 2)
        operations.append(
            (
                Instruction(Opcode.OPCODE_MOV, dst, src_a=src_a),
                "MOV R1, R2",
            )
        )

        # MOV R1, R3
        src_a = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, 3)
        operations.append(
            (Instruction(Opcode.OPCODE_MOV, dst, src_a=src_a), "MOV R1, R3")
        )

        mac_ops = []
        ilu_ops = []
        error = encoding_visitor._distribute_mov_ops(operations, mac_ops, ilu_ops)
        self.assertEqual("more than 1 MOV targets R1", error)

    def test_distribute_two_ilu_mov_non_r1_temporary_fails(self):
        operations = []

        # MOV R0, R2
        dst = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 0)
        src_a = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, 2)
        operations.append(
            (
                Instruction(Opcode.OPCODE_MOV, dst, src_a=src_a),
                "MOV R0, R2",
            )
        )

        # MUL R1, R3, R4
        dst = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 1)
        src_a = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, 3)
        src_b = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, 4)
        mac_ops = [
            (
                Instruction(Opcode.OPCODE_MOV, dst, src_a=src_a, src_b=src_b),
                "MUL R1, R3, R4",
            )
        ]

        ilu_ops = []
        error = encoding_visitor._distribute_mov_ops(operations, mac_ops, ilu_ops)
        self.assertEqual(
            "ILU operation may not target non-R1 temporary registers", error
        )

    def _mul_r2(self):
        dst = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 2)
        src_a = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, 8)
        src_b = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, 9)
        op = Instruction(Opcode.OPCODE_MUL, dst, src_a=src_a, src_b=src_b)
        src = f"MUL R2, R8, R9"
        return op, src

    def _mov_r1(self, input_r: int = 0):
        dst = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 1)
        src_a = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, input_r)
        op = Instruction(Opcode.OPCODE_MOV, dst, src_a=src_a)
        src = f"MOV R1, R{input_r}"
        return op, src

    def _mov_opos(self, input_r: int = 0):
        dst = DestinationRegister(RegisterFile.PROGRAM_OUTPUT, OutputRegisters.REG_POS)
        src_a = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, input_r)
        op = Instruction(Opcode.OPCODE_MOV, dst, src_a=src_a)
        src = f"MOV oPos, R{input_r}"
        return op, src

    def _mov_r2(self, input_r: int = 0):
        dst = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 2)
        src_a = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, input_r)
        op = Instruction(Opcode.OPCODE_MOV, dst, src_a=src_a)
        src = f"MOV R2, R{input_r}"
        return op, src

    def test_distribute_mac_r1_o(self):
        r1 = self._mov_r1()
        opos = self._mov_opos()

        operations = [r1, opos]
        mac_ops = []
        ilu_ops = []
        error = encoding_visitor._distribute_mov_ops(operations, mac_ops, ilu_ops)
        self.assertEqual("", error)

        self.assertEqual(1, len(mac_ops))
        self.assertEqual(0, len(ilu_ops))

        combined_op = opos[0]
        combined_op.secondary_dst_reg = r1[0].dst_reg
        self.assertEqual(combined_op, mac_ops[0][0])

        combined_src = f"{opos[1]} + {r1[1]}"
        self.assertEqual(combined_src, mac_ops[0][1])

    def test_distribute_mac_r2_o(self):
        r2 = self._mov_r2()
        opos = self._mov_opos()

        operations = [r2, opos]
        mac_ops = []
        ilu_ops = []
        error = encoding_visitor._distribute_mov_ops(operations, mac_ops, ilu_ops)
        self.assertEqual("", error)

        self.assertEqual(1, len(mac_ops))
        self.assertEqual(0, len(ilu_ops))

        combined_op = opos[0]
        combined_op.secondary_dst_reg = r2[0].dst_reg
        self.assertEqual(combined_op, mac_ops[0][0])

        combined_src = f"{opos[1]} + {r2[1]}"
        self.assertEqual(combined_src, mac_ops[0][1])

    def test_distribute_mac_o_ilu_r1(self):
        r1 = self._mov_r1(5)
        opos = self._mov_opos()

        operations = [r1, opos]
        mac_ops = []
        ilu_ops = []
        error = encoding_visitor._distribute_mov_ops(operations, mac_ops, ilu_ops)
        self.assertEqual("", error)

        self.assertEqual(1, len(mac_ops))
        self.assertEqual(1, len(ilu_ops))

        self.assertEqual(opos, mac_ops[0])
        self.assertEqual(r1, ilu_ops[0])

    def test_distribute_mac_r2_o_ilu_r1(self):
        r1 = self._mov_r1(5)
        r2 = self._mov_r2()
        opos = self._mov_opos()

        operations = [r1, r2, opos]
        mac_ops = []
        ilu_ops = []
        error = encoding_visitor._distribute_mov_ops(operations, mac_ops, ilu_ops)
        self.assertEqual("", error)

        self.assertEqual(1, len(mac_ops))
        self.assertEqual(1, len(ilu_ops))

        combined_op = opos[0]
        combined_op.secondary_dst_reg = r2[0].dst_reg
        self.assertEqual(combined_op, mac_ops[0][0])

        combined_src = f"{opos[1]} + {r2[1]}"
        self.assertEqual(combined_src, mac_ops[0][1])

        self.assertEqual(r1, ilu_ops[0])

    def test_distribute_mac_r2_ilu_o(self):
        r2 = self._mov_r2()
        opos = self._mov_opos(5)

        operations = [r2, opos]
        mac_ops = []
        ilu_ops = []
        error = encoding_visitor._distribute_mov_ops(operations, mac_ops, ilu_ops)
        self.assertEqual("", error)

        self.assertEqual(1, len(mac_ops))
        self.assertEqual(1, len(ilu_ops))

        self.assertEqual(r2, mac_ops[0])
        self.assertEqual(opos, ilu_ops[0])

    def test_distribute_mac_r2_ilu_r1(self):
        r2 = self._mov_r2()
        r1 = self._mov_r1(5)

        operations = [r2, r1]
        mac_ops = []
        ilu_ops = []
        error = encoding_visitor._distribute_mov_ops(operations, mac_ops, ilu_ops)
        self.assertEqual("", error)

        self.assertEqual(1, len(mac_ops))
        self.assertEqual(1, len(ilu_ops))

        self.assertEqual(r2, mac_ops[0])
        self.assertEqual(r1, ilu_ops[0])

    def test_distribute_mac_r2_ilu_r1_o(self):
        r2 = self._mov_r2()
        r1 = self._mov_r1(5)
        opos = self._mov_opos(5)

        operations = [r2, r1, opos]
        mac_ops = []
        ilu_ops = []
        error = encoding_visitor._distribute_mov_ops(operations, mac_ops, ilu_ops)
        self.assertEqual("", error)

        self.assertEqual(1, len(mac_ops))
        self.assertEqual(1, len(ilu_ops))

        self.assertEqual(r2, mac_ops[0])

        combined_op = opos[0]
        combined_op.secondary_dst_reg = r1[0].dst_reg
        self.assertEqual(combined_op, ilu_ops[0][0])

        combined_src = f"{opos[1]} + {r1[1]}"
        self.assertEqual(combined_src, ilu_ops[0][1])

    def test_distribute_mac_mul_ilu_o(self):
        mul = self._mul_r2()
        opos = self._mov_opos(5)
        operations = [mul, opos]
        mac_ops = []
        ilu_ops = []
        error = encoding_visitor._distribute_mov_ops(operations, mac_ops, ilu_ops)
        self.assertEqual("", error)

        self.assertEqual(1, len(mac_ops))
        self.assertEqual(1, len(ilu_ops))

        self.assertEqual(mul, mac_ops[0])
        self.assertEqual(opos, ilu_ops[0])

    def test_distribute_mac_mul_ilu_r1(self):
        mul = self._mul_r2()
        r1 = self._mov_r1(5)
        operations = [mul, r1]
        mac_ops = []
        ilu_ops = []
        error = encoding_visitor._distribute_mov_ops(operations, mac_ops, ilu_ops)
        self.assertEqual("", error)

        self.assertEqual(1, len(mac_ops))
        self.assertEqual(1, len(ilu_ops))

        self.assertEqual(mul, mac_ops[0])
        self.assertEqual(r1, ilu_ops[0])

    def test_distribute_mac_mul_ilu_r1_o(self):
        mul = self._mul_r2()
        r1 = self._mov_r1(5)
        opos = self._mov_opos(5)
        operations = [mul, r1, opos]
        mac_ops = []
        ilu_ops = []
        error = encoding_visitor._distribute_mov_ops(operations, mac_ops, ilu_ops)
        self.assertEqual("", error)

        self.assertEqual(1, len(mac_ops))
        self.assertEqual(1, len(ilu_ops))

        self.assertEqual(mul, mac_ops[0])

        combined_op = opos[0]
        combined_op.secondary_dst_reg = r1[0].dst_reg
        self.assertEqual(combined_op, ilu_ops[0][0])

        combined_src = f"{opos[1]} + {r1[1]}"
        self.assertEqual(combined_src, ilu_ops[0][1])


class VSHEncoderCombinedOperationsTestCase(unittest.TestCase):
    """Tests processing of combined MAC+ILU and multi-output operations."""

    def _mul_r9(self, input_1_r: int = 0, input_2_r: int = 10):
        dst = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 9)
        src_a = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, input_1_r)
        src_b = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, input_2_r)
        return (
            Instruction(Opcode.OPCODE_MUL, dst, src_a=src_a, src_b=src_b),
            f"MUL R9, R{input_1_r}, R{input_2_r}",
        )

    def _mul_opos(self, input_1_r: int = 0, input_2_r: int = 10):
        dst = DestinationRegister(RegisterFile.PROGRAM_OUTPUT, OutputRegisters.REG_POS)
        src_a = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, input_1_r)
        src_b = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, input_2_r)
        return (
            Instruction(Opcode.OPCODE_MUL, dst, src_a=src_a, src_b=src_b),
            f"MUL oPos, R{input_1_r}, R{input_2_r}",
        )

    def _add_r9(self, input_1_r: int = 0, input_2_r: int = 10):
        dst = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 9)
        src_a = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, input_1_r)
        src_b = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, input_2_r)
        return (
            Instruction(Opcode.OPCODE_ADD, dst, src_a=src_a, src_b=src_b),
            f"ADD R9, R{input_1_r}.wxz, R{input_2_r}",
        )

    def _add_opos(self, input_1_r: int = 0, input_2_r: int = 10):
        dst = DestinationRegister(RegisterFile.PROGRAM_OUTPUT, OutputRegisters.REG_POS)
        src_a = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, input_1_r)
        src_b = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, input_2_r)
        return (
            Instruction(Opcode.OPCODE_ADD, dst, src_a=src_a, src_b=src_b),
            f"ADD oPos, R{input_1_r}.wxz, R{input_2_r}",
        )

    def _rsq_r1(self, input_r: int = 0):
        dst = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 1)
        src_a = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, input_r)
        return Instruction(Opcode.OPCODE_RSQ, dst, src_a=src_a), f"RSQ R1, R{input_r}"

    def _rsq_opos(self, input_r: int = 0):
        dst = DestinationRegister(RegisterFile.PROGRAM_OUTPUT, OutputRegisters.REG_POS)
        src_a = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, input_r)
        return Instruction(Opcode.OPCODE_RSQ, dst, src_a=src_a), f"RSQ oPos, R{input_r}"

    def _rcp_r1(self, input_r: int = 0):
        dst = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 1)
        src_a = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, input_r)
        return Instruction(Opcode.OPCODE_RCP, dst, src_a=src_a), f"RCP R1, R{input_r}"

    def _rcp_opos(self, input_r: int = 0):
        dst = DestinationRegister(RegisterFile.PROGRAM_OUTPUT, OutputRegisters.REG_POS)
        src_a = SourceRegister(RegisterFile.PROGRAM_TEMPORARY, input_r)
        return Instruction(Opcode.OPCODE_RCP, dst, src_a=src_a), f"RCP oPos, R{input_r}"

    def test_double_mac_different_inputs_fails(self):
        operations = [self._mul_r9(), self._mul_opos(5)]

        with self.assertRaises(encoding_visitor.EncodingError) as err:
            encoding_visitor.process_combined_operations(operations)
        self.assertEqual(
            "Conflicting MAC operations (operations have different inputs) at 0",
            str(err.exception),
        )

    def test_conflicting_mac_ops_fails(self):
        operations = [self._mul_r9(), self._add_opos()]

        with self.assertRaises(encoding_visitor.EncodingError) as err:
            encoding_visitor.process_combined_operations(operations)
        self.assertEqual(
            "Conflicting MAC operations (conflicting operations) at 0",
            str(err.exception),
        )

    def test_double_ilu_different_inputs_fails(self):
        operations = [self._rsq_r1(), self._rsq_opos(5)]

        with self.assertRaises(encoding_visitor.EncodingError) as err:
            encoding_visitor.process_combined_operations(operations)
        self.assertEqual(
            "Conflicting ILU operations (operations have different inputs) at 0",
            str(err.exception),
        )

    def test_conflicting_ilu_ops_fails(self):
        operations = [self._rsq_opos(), self._rcp_r1()]

        with self.assertRaises(encoding_visitor.EncodingError) as err:
            encoding_visitor.process_combined_operations(operations)
        self.assertEqual(
            "Conflicting ILU operations (conflicting operations) at 0",
            str(err.exception),
        )

    def test_mul_r9_o(self):
        r9 = self._mul_r9()
        opos = self._mul_opos()
        operations = [r9, opos]
        result = encoding_visitor.process_combined_operations(operations)

        combined_op = opos[0]
        combined_op.secondary_dst_reg = r9[0].dst_reg
        self.assertEqual(combined_op, result[0])

        combined_src = f"{opos[1]} + {r9[1]}"
        self.assertEqual(combined_src, result[1])

    def test_rcp_r9_o(self):
        r1 = self._rcp_r1()
        opos = self._rcp_opos()
        operations = [r1, opos]
        result = encoding_visitor.process_combined_operations(operations)

        combined_op = opos[0]
        combined_op.secondary_dst_reg = r1[0].dst_reg
        self.assertEqual(combined_op, result[0])

        combined_src = f"{opos[1]} + {r1[1]}"
        self.assertEqual(combined_src, result[1])

    def test_mul_rcp(self):
        r1 = self._rcp_r1()
        opos = self._rcp_opos()
        r9 = self._mul_r9()
        operations = [r1, opos, r9]
        result = encoding_visitor.process_combined_operations(operations)

        combined_op = r9[0]

        combined_op.paired_ilu_opcode = opos[0].opcode
        combined_op.paired_ilu_dst_reg = opos[0].dst_reg
        combined_op.paired_ilu_secondary_dst_reg = r1[0].dst_reg
        combined_op.src_reg[2] = opos[0].src_reg[0]
        self.assertEqual(combined_op, result[0])

        combined_src = f"{opos[1]} + {r1[1]}"
        self.assertEqual(f"{r9[1]} + {combined_src}", result[1])

    def test_add_rcp_with_different_c_input_fails(self):
        r1 = self._rcp_r1()
        opos = self._rcp_opos()
        r9 = self._add_r9(input_2_r=4)
        operations = [r1, opos, r9]

        with self.assertRaises(encoding_visitor.EncodingError) as err:
            encoding_visitor.process_combined_operations(operations)
        self.assertEqual(
            "Invalid instruction pairing (MAC operation uses input C which does not match ILU input)",
            str(err.exception),
        )

    def test_add_rcp_with_same_c_input(self):
        r1 = self._rcp_r1()
        opos = self._rcp_opos()
        r9 = self._add_r9(input_1_r=10, input_2_r=0)
        operations = [r1, opos, r9]
        result = encoding_visitor.process_combined_operations(operations)

        combined_op = r9[0]

        combined_op.paired_ilu_opcode = opos[0].opcode
        combined_op.paired_ilu_dst_reg = opos[0].dst_reg
        combined_op.paired_ilu_secondary_dst_reg = r1[0].dst_reg
        combined_op.src_reg[2] = opos[0].src_reg[0]
        self.assertEqual(combined_op, result[0])

        combined_src = f"{opos[1]} + {r1[1]}"
        self.assertEqual(f"{r9[1]} + {combined_src}", result[1])


if __name__ == "__main__":
    unittest.main()
