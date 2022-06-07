"""Tests for disassembler functionality."""

# pylint: disable=missing-function-docstring
# pylint: disable=protected-access
# pylint: disable=too-many-public-methods
# pylint: disable=wrong-import-order

import unittest

from nv2avsh import disassemble
import io


class DisassemblerTestCase(unittest.TestCase):
    """Tests for disassembler functionality."""

    def test_text_input_parser_empty(self):
        test = io.StringIO("")
        result = disassemble._parse_text_input(test)
        self.assertEqual([], result)

    def test_text_input_parser_valid_single_line_one_instruction(self):
        test = io.StringIO("0x0,0x1,0x2,0x3")
        result = disassemble._parse_text_input(test)
        self.assertEqual([[0, 1, 2, 3]], result)

    def test_text_input_parser_valid_multiple_lines_one_instruction(self):
        test = io.StringIO("0x0,0x1,\n\t0x2,   0x3  ")
        result = disassemble._parse_text_input(test)
        self.assertEqual([[0, 1, 2, 3]], result)

    def test_text_input_parser_valid_single_line_multiple_instructions(self):
        test = io.StringIO("0x0,0x1,0x2,0x3")
        result = disassemble._parse_text_input(test)
        self.assertEqual([[0, 1, 2, 3]], result)

    def test_text_input_parser_valid_multiple_lines_multiple_instructions(self):
        test = io.StringIO("0x0,0x1,0x2,0x3")
        result = disassemble._parse_text_input(test)
        self.assertEqual([[0, 1, 2, 3]], result)

    def test_disassembler_empty(self):
        test = []
        result = disassemble.disassemble(test, False)
        self.assertEqual([], result)

    def test_disassembler_single_no_explain(self):
        def _test(expected, value):
            result = disassemble.disassemble([value], False)
            self.assertEqual([expected], result)

        _test("MOV oT2.xyzw, v11", [0x00000000, 0x0020161B, 0x0836106C, 0x2070F858])
        _test(
            "MAD oPos.xyz, R12, R1.x, c[59]",
            [0x00000000, 0x0087601B, 0xC400286C, 0x3070E801],
        )
        _test(
            "DP4 oPos.z, v0, c[100]", [0x00000000, 0x00EC801B, 0x0836186C, 0x20702800]
        )

        # This is an ambiguous pair, there are differences in unused mappings.
        _test(
            "MAD R0.z, R0.z, c[117].z, -c[117].w",
            [0x00000000, 0x008EA0AA, 0x05541FFC, 0x32000FF8],
        )
        _test(
            "MAD R0.z, R0.z, c[117].z, -c[117].w",
            [0x00000000, 0x008EA0AA, 0x0554BFFD, 0x72000000],
        )

        _test(
            "MUL R2.xyzw, R1, c[0] + MOV oD1.xyzw, v4",
            [0x00000000, 0x0240081B, 0x1436186C, 0x2F20F824],
        )

        _test(
            "MOV oD0.xyzw, v3 + RCP R1.w, R1.w",
            [0x00000000, 0x0420061B, 0x083613FC, 0x5011F818],
        )

        _test("ARL A0, R0.x", [0x00000000, 0x01A00000, 0x0436106C, 0x20700FF8])

        _test(
            "ADD R0.xy, c[A0+121].zw, -c[A0+121].xy",
            [0x00000000, 0x006F20BF, 0x9C001456, 0x7C000002],
        )

        _test(
            "RCP oFog.xyzw, v0.w",
            [0x00000000, 0x0400001B, 0x083613FC, 0x2070F82C],
        )

        _test(
            "MUL oPos.xyz, R12.xyz, c[58].xyz",
            [0x00000000, 0x0047401A, 0xC434186C, 0x2070E800],
        )

    def test_disassembler_multi_output_no_explain(self):
        def _test(expected, value):
            result = disassemble.disassemble([value], False)
            self.assertEqual([expected], result)

        _test(
            "DP4 oPos.z, R6, c[98] + DP4 R0.x, R6, c[98]",
            [0x00000000, 0x00EC401B, 0x64365800, 0x28002800],
        )

    def test_disassembler_constant_register_output_no_explain(self):
        def _test(expected, value):
            result = disassemble.disassemble([value], False)
            self.assertEqual([expected], result)

        _test(
            "DPH c[15].xy, v4, c[10]",
            [0x00000000, 0x00C1481B, 0x0836186C, 0x2070C078],
        )


if __name__ == "__main__":
    unittest.main()
