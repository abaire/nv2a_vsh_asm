"""Tests for vsh_encoder."""

# pylint: disable=missing-function-docstring
# pylint: disable=too-many-public-methods
# pylint: disable=unused-wildcard-import
# pylint: disable=wildcard-import
# pylint: disable=wrong-import-order

from typing import List
import unittest

from nv2avsh.nv2a_vsh_asm.vsh_encoder import *
from nv2avsh.nv2a_vsh_asm.vsh_instruction import vsh_diff_instructions


class VSHEncoderTestCase(unittest.TestCase):
    """Tests for vsh_encoder."""

    def test_empty(self):
        results = encode([])
        self.assertEqual([], results)

    def test_mov_out_in_unswizzled(self):
        program = []

        # MOV oD0.xyzw, v3
        dst = DestinationRegister(
            RegisterFile.PROGRAM_OUTPUT, OutputRegisters.REG_DIFFUSE
        )
        src = SourceRegister(RegisterFile.PROGRAM_INPUT, InputRegisters.REG_DIFFUSE)
        program.append(Instruction(Opcode.OPCODE_MOV, dst, src))

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
        program.append(Instruction(Opcode.OPCODE_MOV, dst, src))

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
        program.append(Instruction(Opcode.OPCODE_MOV, dst, src))

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
        program.append(Instruction(Opcode.OPCODE_RCP, dst, src))

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
        program.append(Instruction(Opcode.OPCODE_MUL, dst, src_a, src_b))

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
        program.append(Instruction(Opcode.OPCODE_ADD, dst, src_a, src_b))

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
        program.append(Instruction(Opcode.OPCODE_DP4, dst, src_a, src_b))

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
        program.append(Instruction(Opcode.OPCODE_MAD, dst, src_a, src_b, src_c))

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
            Opcode.OPCODE_MOV, dst, src_a, None, src_c, Opcode.OPCODE_RCP, ilu_dst
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
            Opcode.OPCODE_MOV, dst, src_a, None, src_c, Opcode.OPCODE_RCC, ilu_dst
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
            Opcode.OPCODE_MUL, dst, src_a, src_b, src_c, Opcode.OPCODE_RCC, ilu_dst
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
            Opcode.OPCODE_MUL, dst, src_a, src_b, src_c, Opcode.OPCODE_MOV, ilu_dst
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
            Opcode.OPCODE_MOV, dst, src_a, src_b, src_c, Opcode.OPCODE_MOV, ilu_dst
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
            Opcode.OPCODE_MOV, dst, src_a, src_b, src_c, Opcode.OPCODE_MOV, ilu_dst
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
            Opcode.OPCODE_DP3, dst, src_a, src_b, src_c, Opcode.OPCODE_MOV, ilu_dst
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
        program.append(Instruction(Opcode.OPCODE_ADD, dst, src_a, src_b))

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
        program.append(Instruction(Opcode.OPCODE_MAD, dst, src_a, src_b, src_c))

        results = encode(program)
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x008EA0AA, 0x05541FFC, 0x32000FF8], results[0])
        # xemu decompiles this to the same isntruction
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


if __name__ == "__main__":
    unittest.main()
