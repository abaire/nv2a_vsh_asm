from typing import List
import unittest

from nv2a_vsh_asm.assembler import Assembler
from nv2a_vsh_asm import vsh_encoder


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

    def _assert_final_marker(self, results):
        self.assertEqual([0, 0, 0, 1], results[-1])

    def _assert_vsh(self, expected: List[int], actual: List[int]):
        diff = vsh_encoder.vsh_diff_instructions(expected, actual)
        self.assertEqual("", diff)


if __name__ == "__main__":
    unittest.main()
