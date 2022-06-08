"""End to end tests for the assembler."""

# pylint: disable=missing-function-docstring
# pylint: disable=too-many-public-methods
# pylint: disable=wrong-import-order

import pathlib
import os
import re
from typing import List
import unittest

from nv2avsh.nv2a_vsh_asm.assembler import Assembler
from nv2avsh.nv2a_vsh_asm import vsh_instruction

_RESOURCE_PATH = os.path.dirname(pathlib.Path(__file__).resolve())

_HEX_MATCH = r"0x[0-9a-fA-F]+"
# // [0x00000000, 0x0400001B, 0x083613FC, 0x2070F82C]
_EXPECTED_OUTPUT_RE = re.compile(
    r"^\s*//\s*\[\s*("
    + _HEX_MATCH
    + r"),\s*("
    + _HEX_MATCH
    + r"),\s*("
    + _HEX_MATCH
    + r"),\s*("
    + _HEX_MATCH
    + r")\s*]\s*$",
    re.MULTILINE,
)


def _extract_expected_instructions(source: str) -> List[List[int]]:
    ret = []

    for match in re.finditer(_EXPECTED_OUTPUT_RE, source):
        ret.append(
            [
                int(match.group(1), 16),
                int(match.group(2), 16),
                int(match.group(3), 16),
                int(match.group(4), 16),
            ]
        )

    return ret


class VSHAssemblerTestCase(unittest.TestCase):
    """End to end tests for the assembler."""

    def test_empty(self):
        asm = Assembler("")
        asm.assemble()

        self.assertEqual([], asm.output)

    def test_mov_out_in_swizzled(self):
        asm = Assembler("MOV oT0.xy,v0.zw")
        asm.assemble()
        results = asm.output
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x002000BF, 0x0836106C, 0x2070C848], results[0])

    def test_bare_const(self):
        asm = Assembler("DPH oT0.x, v4, c15")
        asm.assemble()
        results = asm.output
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x00C1E81B, 0x0836186C, 0x20708848], results[0])

    def test_bracketed_const(self):
        asm = Assembler("DPH oT0.x, v4, c[15]")
        asm.assemble()
        results = asm.output
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x00C1E81B, 0x0836186C, 0x20708848], results[0])

    def test_negated_temp(self):
        asm = Assembler("ADD R6.xyz, c17, -R10")
        asm.assemble()
        results = asm.output
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x0062201B, 0x0C36146E, 0x9E600FF8], results[0])

    def test_negated_temp_swizzle(self):
        asm = Assembler("MAD R11.xyw, -R1.yzxw, R7.zxyw, R10")
        asm.assemble()
        results = asm.output
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x00800163, 0x150EE86E, 0x9DB00FF8], results[0])

    def test_negated_bare_const(self):
        asm = Assembler("DP3 R7.z, R0, -c23")
        asm.assemble()
        results = asm.output
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x00A2E01B, 0x0636186C, 0x22700FF8], results[0])

    def test_negated_bracketed_const(self):
        asm = Assembler("DP3 R7.z, R0, -c[23]")
        asm.assemble()
        results = asm.output
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x00A2E01B, 0x0636186C, 0x22700FF8], results[0])

    def test_negated_bare_const_swizzled(self):
        asm = Assembler("MAD R0.z, R0.z, c[117].z, -c117.w")
        asm.assemble()
        results = asm.output
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x008EA0AA, 0x05541FFC, 0x32000FF8], results[0])
        # xemu decompiles this to the same isntruction
        # self._assert_vsh([0x00000000, 0x008EA0AA, 0x0554BFFD, 0x72000000], results[0])

    def test_negated_bracketed_const_swizzled(self):
        asm = Assembler("MAD R0.z, R0.z, c[117].z, -c[117].w")
        asm.assemble()
        results = asm.output
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x008EA0AA, 0x05541FFC, 0x32000FF8], results[0])
        # xemu decompiles this to the same isntruction
        # self._assert_vsh([0x00000000, 0x008EA0AA, 0x0554BFFD, 0x72000000], results[0])

    # FLD_OUT_R is set to a non-default value despite nothing being written to a temp register
    # + 	FLD_OUT_R 0x9 (1001) != actual 0x7 (0111)
    # def test_negated_bare_const_swizzle(self):
    #     asm = Assembler("MAD oPos.xy, R0.xy, c[96].w, -c96.z")
    #     asm.assemble()
    #     results = asm.output
    #     self._assert_final_marker(results)
    #     self.assertEqual(len(results), 2)
    #     self._assert_vsh([0x00000000, 0x008C0015, 0x05FE1EA8, 0x3090C800], results[0])
    #
    # def test_negated_bracketed_const_swizzle(self):
    #     asm = Assembler("MAD oPos.xy, R0.xy, c[96].w, -c[96].z")
    #     asm.assemble()
    #     results = asm.output
    #     self._assert_final_marker(results)
    #     self.assertEqual(len(results), 2)
    #     self._assert_vsh([0x00000000, 0x008C0015, 0x05FE1EA8, 0x3090C800], results[0])

    def test_relative_const(self):
        asm = Assembler("MUL R3.xyzw, v6.x, c[A0+60]")
        asm.assemble()
        results = asm.output
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x00478C00, 0x0836186C, 0x2F300FFA], results[0])

    def test_relative_const_spaced(self):
        asm = Assembler("MUL R3.xyzw, v6.x, c[ A0   + 60 ]")
        asm.assemble()
        results = asm.output
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x00478C00, 0x0836186C, 0x2F300FFA], results[0])

    def test_relative_const_spaced_a_second(self):
        asm = Assembler("MUL R3.xyzw, v6.x, c[ 60 + A0 ]")
        asm.assemble()
        results = asm.output
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x00478C00, 0x0836186C, 0x2F300FFA], results[0])

    def test_uniform_vector_bare(self):
        asm = Assembler("#test_vector vector 15\n" "DPH oT0.x, v4, #test_vector")
        asm.assemble()
        results = asm.output
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x00C1E81B, 0x0836186C, 0x20708848], results[0])

    def test_uniform_vector_bracketed(self):
        asm = Assembler("#test_vector vector 15\n" "DPH oT0.x, v4, #test_vector[0]")
        asm.assemble()
        results = asm.output
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x00C1E81B, 0x0836186C, 0x20708848], results[0])

    def test_uniform_matrix4_bare(self):
        asm = Assembler("#test_matrix matrix4 15\nDPH oT0.x, v4, #test_matrix")
        asm.assemble()
        results = asm.output
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x00C1E81B, 0x0836186C, 0x20708848], results[0])

    def test_uniform_matrix4_with_zero_offset(self):
        asm = Assembler("#test_matrix matrix4 15\nDPH oT0.x, v4, #test_matrix[0]")
        asm.assemble()
        results = asm.output
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x00C1E81B, 0x0836186C, 0x20708848], results[0])

    def test_uniform_matrix4_with_offset(self):
        asm = Assembler("#test_matrix matrix4 14\nDPH oT0.x, v4, #test_matrix[ 1 ]")
        asm.assemble()
        results = asm.output
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x00C1E81B, 0x0836186C, 0x20708848], results[0])

    def test_uniform_vector_output_bare(self):
        asm = Assembler("#test_vector vector 15\n" "DPH #test_vector, v4, c[10]")
        asm.assemble()
        results = asm.output
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x00C1481B, 0x0836186C, 0x2070F078], results[0])

    def test_uniform_vector_output_indexed(self):
        asm = Assembler("#test_vector vector 15\n" "DPH #test_vector[0], v4, c[10]")
        asm.assemble()
        results = asm.output
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x00C1481B, 0x0836186C, 0x2070F078], results[0])

    def test_uniform_vector_output_bare_swizzle(self):
        asm = Assembler("#test_vector vector 15\n" "DPH #test_vector.xy, v4, c[10]")
        asm.assemble()
        results = asm.output
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x00C1481B, 0x0836186C, 0x2070C078], results[0])

    def test_uniform_vector_output_indexed_swizzle(self):
        asm = Assembler("#test_vector vector 15\n" "DPH #test_vector[0].xy, v4, c[10]")
        asm.assemble()
        results = asm.output
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x00C1481B, 0x0836186C, 0x2070C078], results[0])

    def test_uniform_matrix_output_bare(self):
        asm = Assembler("#test_matrix matrix4 15\n" "DPH #test_matrix, v4, c[10]")
        asm.assemble()
        results = asm.output
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x00C1481B, 0x0836186C, 0x2070F078], results[0])

    def test_uniform_matrix_output_indexed(self):
        asm = Assembler("#test_matrix matrix4 14\n" "DPH #test_matrix[1], v4, c[10]")
        asm.assemble()
        results = asm.output
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x00C1481B, 0x0836186C, 0x2070F078], results[0])

    def test_uniform_matrix_output_bare2(self):
        asm = Assembler("#output matrix4 188\n" "mov #output[0], v3")
        asm.assemble()
        results = asm.output
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x0020061B, 0x0836106C, 0x2070F5E0], results[0])

    def test_paired(self):
        asm = Assembler("MUL R2.xyzw, R1, c[0] + MOV oD1.xyzw, v4")
        asm.assemble()
        results = asm.output
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x0240081B, 0x1436186C, 0x2F20F824], results[0])

    def test_arl(self):
        asm = Assembler("ARL A0, R0.x")
        asm.assemble()
        results = asm.output
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x01A00000, 0x0436106C, 0x20700FF8], results[0])
        # Ambiguous result, it looks like some compilers null out unused fields
        # differently.
        # self._assert_vsh([0x00000000, 0x01A00000, 0x04001000, 0x20000000], results[0])

    def test_rcp(self):
        asm = Assembler("RCP oFog, v0.w")
        asm.assemble()
        results = asm.output
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x0400001B, 0x083613FC, 0x2070F82C], results[0])

    def test_r12(self):
        asm = Assembler("MUL oPos.xyz, R12.xyz, c[58].xyz")
        asm.assemble()
        results = asm.output
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x0047401A, 0xC434186C, 0x2070E800], results[0])
        # Ambiguous result, differs in unused fields.
        # self._assert_vsh([0x00000000, 0x0047401A, 0xC4355800, 0x20A0E800], results[0])

    def test_two_output_instruction(self):
        asm = Assembler("DP4 oPos.z, R6, c[98] + DP4 R0.x, R6, c[98]")
        asm.assemble()
        results = asm.output
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x00EC401B, 0x6436186C, 0x28002800], results[0])
        # Ambiguous result, differs in unused fields.
        # self._assert_vsh([0x00000000, 0x00EC401B, 0x64365800, 0x28002800], results[0])

    def test_paired_ilu_non_r1_temporary_writes_to_r1(self):
        asm = Assembler("DP4 oPos.x, R6, c[96] + RSQ R10.x, R2.x")
        asm.assemble()
        results = asm.output
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x08EC001B, 0x64361800, 0x90188800], results[0])

    def test_simple(self):
        all_input = os.path.join(_RESOURCE_PATH, "simple.vsh")
        with open(all_input) as infile:
            source = infile.read()

        asm = Assembler(source)
        asm.assemble(inline_final_flag=True)
        results = asm.output

        expected_instructions = _extract_expected_instructions(source)
        self.assertEqual(len(results), len(expected_instructions))
        for expected, actual in zip(expected_instructions, results):
            self._assert_vsh(expected, actual)

    def test_ngb_lava(self):
        all_input = os.path.join(_RESOURCE_PATH, "ngb_lava.vsh")
        with open(all_input) as infile:
            source = infile.read()

        asm = Assembler(source)
        asm.assemble(inline_final_flag=True)
        results = asm.output

        expected_instructions = _extract_expected_instructions(source)
        self.assertEqual(len(results), len(expected_instructions))
        for expected, actual in zip(expected_instructions, results):
            self._assert_vsh(expected, actual)

    def test_trivial_end_to_end_shader(self):
        all_input = os.path.join(_RESOURCE_PATH, "set_pos_and_color.vsh")
        with open(all_input) as infile:
            source = infile.read()

        asm = Assembler(source)
        asm.assemble(inline_final_flag=True)
        results = asm.output

        expected_instructions = _extract_expected_instructions(source)
        self.assertEqual(len(results), len(expected_instructions))
        for expected, actual in zip(expected_instructions, results):
            self._assert_vsh(expected, actual)

    def _assert_final_marker(self, results):
        self.assertEqual([0, 0, 0, 1], results[-1])

    def _assert_vsh(self, expected: List[int], actual: List[int]):
        diff = vsh_instruction.vsh_diff_instructions(expected, actual)
        if diff:
            raise self.failureException(diff)


if __name__ == "__main__":
    unittest.main()
