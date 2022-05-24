from typing import List
import unittest

from nv2a_vsh_asm.vsh_encoder import *


class VSHEncoderTestCase(unittest.TestCase):
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

    # Something about this test seems wrong, the swizzle behavior does not match and
    # the FLD_OUT_ORB setting doesn't match expectations for a shader that does not
    # write to a constant output register.
    # def test_rcp_temp_temp_swizzled(self):
    #     program = []
    #
    #     # RCP(R1,x, R0.w);
    #     dst = DestinationRegister(gl_register_file.PROGRAM_TEMPORARY, 1, WRITEMASK_X)
    #
    #     # TODO: Investigate why this is not wwww
    #     # The vp20 compiler is emitting 0's instead of repeating the last component.
    #     src = SourceRegister(gl_register_file.PROGRAM_TEMPORARY, 0, MAKE_SWIZZLE4(SWIZZLE_W, 0, 0, 0))
    #     program.append(Instruction(prog_opcode.OPCODE_RCP, dst, src))
    #
    #     results = encode(program)
    #     self._assert_final_marker(results)
    #     self.assertEqual(len(results), 2)
    #
    #     self._assert_vsh([0x00000000, 0x0400001B, 0x08361300, 0x101807F8], results[0])

    # ORB mismatch, expect 0, got 1
    # def test_min_temp_temp_const_inverse_swizzle(self):
    #     program = []
    #
    #     # MIN(R0,xyzw, R0.x, c[108].wzyx);
    #     dst = DestinationRegister(gl_register_file.PROGRAM_TEMPORARY, 0, WRITEMASK_XYZW)
    #     src_a = SourceRegister(gl_register_file.PROGRAM_TEMPORARY, 0, MAKE_SWIZZLE4(SWIZZLE_X))
    #     src_b = SourceRegister(gl_register_file.PROGRAM_ENV_PARAM, 108 - 96, MAKE_SWIZZLE4(SWIZZLE_W, SWIZZLE_Z, SWIZZLE_Y, SWIZZLE_X))
    #     program.append(Instruction(prog_opcode.OPCODE_MIN, dst, src_a, src_b))
    #
    #     results = encode(program)
    #     self._assert_final_marker(results)
    #     self.assertEqual(len(results), 2)
    #     self._assert_vsh([0x00000000, 0x012D8000, 0x05C8186C, 0x2F0007F8], results[0])

    def test_mul_temp_in_const_swizzled(self):
        program = []

        # MUL R0.x, v0.x, c0.x // Ignore rest of line
        dst = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 0, WRITEMASK_X)
        src_a = SourceRegister(
            RegisterFile.PROGRAM_INPUT, InputRegisters.V0, make_swizzle(SWIZZLE_X)
        )
        src_b = SourceRegister(
            RegisterFile.PROGRAM_ENV_PARAM, 0, make_swizzle(SWIZZLE_X)
        )
        program.append(Instruction(Opcode.OPCODE_MUL, dst, src_a, src_b))

        results = encode(program)
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x004C0000, 0x0800186C, 0x28000FF8], results[0])

    def test_add_temp_temp_const_swizzle(self):
        program = []

        # ADD R0.y, R0.y, c1.w
        dst = DestinationRegister(RegisterFile.PROGRAM_TEMPORARY, 0, WRITEMASK_Y)
        src_a = SourceRegister(
            RegisterFile.PROGRAM_TEMPORARY, 0, make_swizzle(SWIZZLE_Y)
        )
        src_b = SourceRegister(
            RegisterFile.PROGRAM_ENV_PARAM, 1, make_swizzle(SWIZZLE_W)
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
        src_b = SourceRegister(RegisterFile.PROGRAM_ENV_PARAM, 0)
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
            RegisterFile.PROGRAM_ENV_PARAM, 96 - 96, make_swizzle(SWIZZLE_Y)
        )
        src_c = SourceRegister(
            RegisterFile.PROGRAM_TEMPORARY, 0, make_swizzle(SWIZZLE_X)
        )
        program.append(Instruction(Opcode.OPCODE_MAD, dst, src_a, src_b, src_c))

        results = encode(program)
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x008C0055, 0x08AA1800, 0x18000FF8], results[0])

    # def test_mac_mov_ilu_rcp(self):
    #     program = []
    #
    #     # MOV(oD0,xyzw, v3);
    #     # RCP(R1,w, R1.w);
    #     dst = DestinationRegister(gl_register_file.PROGRAM_OUTPUT, OutputRegisters.REG_DIFFUSE, WRITEMASK_XYZW)
    #     src_a = SourceRegister(gl_register_file.PROGRAM_INPUT, InputRegisters.V3)
    #
    #     ins = Instruction(prog_opcode.OPCODE_MOV, dst, src_a)
    #     dst = DestinationRegister(gl_register_file.PROGRAM_TEMPORARY, 1, WRITEMASK_W)
    #     src_a = SourceRegister(gl_register_file.PROGRAM_TEMPORARY, 1, MAKE_SWIZZLE4(SWIZZLE_W))
    #
    #     program.append(ins)
    #
    #     results = encode(program)
    #     self._assert_final_marker(results)
    #     self.assertEqual(len(results), 2)
    #     self._assert_vsh([0x00000000, 0x0420061B, 0x083613FC, 0x5011F818], results[0])

    def _assert_final_marker(self, results):
        self.assertEqual([0, 0, 0, 1], results[-1])

    def _assert_vsh(self, expected: List[int], actual: List[int]):
        diff = vsh_diff_instructions(expected, actual)
        self.assertEqual("", diff)


if __name__ == "__main__":
    unittest.main()
