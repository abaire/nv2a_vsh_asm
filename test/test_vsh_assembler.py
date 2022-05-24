import pathlib
import os
import re
from typing import List
import unittest

from nv2a_vsh_asm.assembler import Assembler
from nv2a_vsh_asm import vsh_encoder

_RESOURCE_PATH = os.path.dirname(pathlib.Path(__file__).resolve())

_HEX_MATCH = r"0x[0-9a-fA-F]+"
# // [0x00000000, 0x0400001B, 0x083613FC, 0x2070F82C]
_EXPECTED_OUTPUT_RE = re.compile(
    r"^\s*//\s*\[\s*("
    + _HEX_MATCH
    + "),\s*("
    + _HEX_MATCH
    + "),\s*("
    + _HEX_MATCH
    + "),\s*("
    + _HEX_MATCH
    + ")\s*]\s*$",
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
        self._assert_vsh([0x00000000, 0x008EA0AA, 0x0554BFFD, 0x72000000], results[0])

    def test_negated_bracketed_const_swizzled(self):
        asm = Assembler("MAD R0.z, R0.z, c[117].z, -c[117].w")
        asm.assemble()
        results = asm.output
        self._assert_final_marker(results)
        self.assertEqual(len(results), 2)
        self._assert_vsh([0x00000000, 0x008EA0AA, 0x0554BFFD, 0x72000000], results[0])

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

    # def test_relative_const(self):
    #     asm = Assembler("MUL R3.xyzw, v6.x, c[A0+60]")
    #     asm.assemble()
    #     results = asm.output
    #     self._assert_final_marker(results)
    #     self.assertEqual(len(results), 2)
    #     self._assert_vsh([0x00000000, 0x00478C00, 0x0836186C, 0x2F300FFA], results[0])
    #
    # def test_relative_const_spaced(self):
    #     asm = Assembler("MUL R3.xyzw, v6.x, c[ A0   + 60 ]")
    #     asm.assemble()
    #     results = asm.output
    #     self._assert_final_marker(results)
    #     self.assertEqual(len(results), 2)
    #     self._assert_vsh([0x00000000, 0x00478C00, 0x0836186C, 0x2F300FFA], results[0])
    #
    # def test_relative_const_spaced_a_second(self):
    #     asm = Assembler("MUL R3.xyzw, v6.x, c[ 60 + A0 ]")
    #     asm.assemble()
    #     results = asm.output
    #     self._assert_final_marker(results)
    #     self.assertEqual(len(results), 2)
    #     self._assert_vsh([0x00000000, 0x00478C00, 0x0836186C, 0x2F300FFA], results[0])

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

    def _assert_final_marker(self, results):
        self.assertEqual([0, 0, 0, 1], results[-1])

    def _assert_vsh(self, expected: List[int], actual: List[int]):
        diff = vsh_encoder.vsh_diff_instructions(expected, actual)
        self.assertEqual("", diff)


if __name__ == "__main__":
    unittest.main()
