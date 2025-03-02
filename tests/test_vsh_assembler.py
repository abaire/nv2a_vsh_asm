"""End to end tests for the assembler."""

# pylint: disable=missing-function-docstring
# pylint: disable=too-many-public-methods
# pylint: disable=wrong-import-order

from __future__ import annotations

import os
import pathlib
import re

import pytest

from nv2a_vsh.nv2a_vsh_asm import vsh_instruction
from nv2a_vsh.nv2a_vsh_asm.assembler import Assembler

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


def _extract_expected_instructions(source: str) -> list[list[int]]:
    return [
        [
            int(match.group(1), 16),
            int(match.group(2), 16),
            int(match.group(3), 16),
            int(match.group(4), 16),
        ]
        for match in re.finditer(_EXPECTED_OUTPUT_RE, source)
    ]


def test_empty():
    asm = Assembler("")
    asm.assemble()

    assert [] == asm.output


def test_mov_out_in_swizzled():
    asm = Assembler("MOV oT0.xy,v0.zw")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 2
    _assert_vsh([0x00000000, 0x002000BF, 0x0836106C, 0x2070C848], results[0])


def test_bare_const():
    asm = Assembler("DPH oT0.x, v4, c15")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 2
    _assert_vsh([0x00000000, 0x00C1E81B, 0x0836186C, 0x20708848], results[0])


def test_bracketed_const():
    asm = Assembler("DPH oT0.x, v4, c[15]")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 2
    _assert_vsh([0x00000000, 0x00C1E81B, 0x0836186C, 0x20708848], results[0])


def test_negated_temp():
    asm = Assembler("ADD R6.xyz, c17, -R10")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 2
    _assert_vsh([0x00000000, 0x0062201B, 0x0C36146E, 0x9E600FF8], results[0])


def test_negated_temp_swizzle():
    asm = Assembler("MAD R11.xyw, -R1.yzxw, R7.zxyw, R10")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 2
    _assert_vsh([0x00000000, 0x00800163, 0x150EE86E, 0x9DB00FF8], results[0])


def test_negated_bare_const():
    asm = Assembler("DP3 R7.z, R0, -c23")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 2
    _assert_vsh([0x00000000, 0x00A2E01B, 0x0636186C, 0x22700FF8], results[0])


def test_negated_bracketed_const():
    asm = Assembler("DP3 R7.z, R0, -c[23]")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 2
    _assert_vsh([0x00000000, 0x00A2E01B, 0x0636186C, 0x22700FF8], results[0])


def test_negated_bare_const_swizzled():
    asm = Assembler("MAD R0.z, R0.z, c[117].z, -c117.w")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 2
    _assert_vsh([0x00000000, 0x008EA0AA, 0x05541FFC, 0x32000FF8], results[0])
    # xemu decompiles this to the same isntruction
    # _assert_vsh([0x00000000, 0x008EA0AA, 0x0554BFFD, 0x72000000], results[0])


def test_negated_bracketed_const_swizzled():
    asm = Assembler("MAD R0.z, R0.z, c[117].z, -c[117].w")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 2
    _assert_vsh([0x00000000, 0x008EA0AA, 0x05541FFC, 0x32000FF8], results[0])
    # xemu decompiles this to the same isntruction
    # _assert_vsh([0x00000000, 0x008EA0AA, 0x0554BFFD, 0x72000000], results[0])


# FLD_OUT_R is set to a non-default value despite nothing being written to a temp register
# + 	FLD_OUT_R 0x9 (1001) != actual 0x7 (0111)
# def test_negated_bare_const_swizzle():
#     asm = Assembler("MAD oPos.xy, R0.xy, c[96].w, -c96.z")
#     asm.assemble()
#     results = asm.output
#     _assert_final_marker(results)
#     assert len(results) == 2
#     _assert_vsh([0x00000000, 0x008C0015, 0x05FE1EA8, 0x3090C800], results[0])
#
# def test_negated_bracketed_const_swizzle():
#     asm = Assembler("MAD oPos.xy, R0.xy, c[96].w, -c[96].z")
#     asm.assemble()
#     results = asm.output
#     _assert_final_marker(results)
#     assert len(results) == 2
#     _assert_vsh([0x00000000, 0x008C0015, 0x05FE1EA8, 0x3090C800], results[0])


def test_relative_const():
    asm = Assembler("MUL R3.xyzw, v6.x, c[A0+60]")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 2
    _assert_vsh([0x00000000, 0x00478C00, 0x0836186C, 0x2F300FFA], results[0])


def test_relative_const_spaced():
    asm = Assembler("MUL R3.xyzw, v6.x, c[ A0   + 60 ]")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 2
    _assert_vsh([0x00000000, 0x00478C00, 0x0836186C, 0x2F300FFA], results[0])


def test_relative_const_spaced_a_second():
    asm = Assembler("MUL R3.xyzw, v6.x, c[ 60 + A0 ]")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 2
    _assert_vsh([0x00000000, 0x00478C00, 0x0836186C, 0x2F300FFA], results[0])


def test_uniform_missing_type():
    asm = Assembler("#missing_type 96\n")

    with pytest.raises(ValueError, match=re.escape("Uniform macro missing type type declaration on line 1")):
        asm.assemble()


def test_uniform_missing_index():
    asm = Assembler("#missing_index vector\n")

    with pytest.raises(ValueError, match=re.escape("Uniform macro missing constant index on line 1")):
        asm.assemble()


def test_uniform_vector_bare():
    asm = Assembler("#test_vector vector 15\n" "DPH oT0.x, v4, #test_vector")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 2
    _assert_vsh([0x00000000, 0x00C1E81B, 0x0836186C, 0x20708848], results[0])


def test_uniform_vector_bracketed():
    asm = Assembler("#test_vector vector 15\n" "DPH oT0.x, v4, #test_vector[0]")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 2
    _assert_vsh([0x00000000, 0x00C1E81B, 0x0836186C, 0x20708848], results[0])


def test_uniform_matrix4_bare():
    asm = Assembler("#test_matrix matrix4 15\nDPH oT0.x, v4, #test_matrix")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 2
    _assert_vsh([0x00000000, 0x00C1E81B, 0x0836186C, 0x20708848], results[0])


def test_uniform_matrix4_with_zero_offset():
    asm = Assembler("#test_matrix matrix4 15\nDPH oT0.x, v4, #test_matrix[0]")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 2
    _assert_vsh([0x00000000, 0x00C1E81B, 0x0836186C, 0x20708848], results[0])


def test_uniform_matrix4_with_offset():
    asm = Assembler("#test_matrix matrix4 14\nDPH oT0.x, v4, #test_matrix[ 1 ]")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 2
    _assert_vsh([0x00000000, 0x00C1E81B, 0x0836186C, 0x20708848], results[0])


def test_uniform_vector_output_bare():
    asm = Assembler("#test_vector vector 15\n" "DPH #test_vector, v4, c[10]")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 2
    _assert_vsh([0x00000000, 0x00C1481B, 0x0836186C, 0x2070F078], results[0])


def test_uniform_vector_output_indexed():
    asm = Assembler("#test_vector vector 15\n" "DPH #test_vector[0], v4, c[10]")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 2
    _assert_vsh([0x00000000, 0x00C1481B, 0x0836186C, 0x2070F078], results[0])


def test_uniform_vector_output_bare_swizzle():
    asm = Assembler("#test_vector vector 15\n" "DPH #test_vector.xy, v4, c[10]")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 2
    _assert_vsh([0x00000000, 0x00C1481B, 0x0836186C, 0x2070C078], results[0])


def test_uniform_vector_output_indexed_swizzle():
    asm = Assembler("#test_vector vector 15\n" "DPH #test_vector[0].xy, v4, c[10]")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 2
    _assert_vsh([0x00000000, 0x00C1481B, 0x0836186C, 0x2070C078], results[0])


def test_uniform_matrix_output_bare():
    asm = Assembler("#test_matrix matrix4 15\n" "DPH #test_matrix, v4, c[10]")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 2
    _assert_vsh([0x00000000, 0x00C1481B, 0x0836186C, 0x2070F078], results[0])


def test_uniform_matrix_output_indexed():
    asm = Assembler("#test_matrix matrix4 14\n" "DPH #test_matrix[1], v4, c[10]")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 2
    _assert_vsh([0x00000000, 0x00C1481B, 0x0836186C, 0x2070F078], results[0])


def test_uniform_matrix_output_bare2():
    asm = Assembler("#output matrix4 188\n" "mov #output[0], v3")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 2
    _assert_vsh([0x00000000, 0x0020061B, 0x0836106C, 0x2070F5E0], results[0])


def test_matmul4x4_too_few_parameters():
    asm = Assembler("#test_matrix matrix4 14\n" "%matmul4x4 r0")
    with pytest.raises(ValueError, match=re.escape("Invalid parameters to %matmul4x4 on line 2")):
        asm.assemble()


def test_matmul4x4_invalid_matrix_uniform_parameter_not_defined():
    asm = Assembler("#test_matrix matrix4 14\n" "%matmul4x4 r0 r0 r0")
    with pytest.raises(ValueError, match=re.escape("Invalid matrix uniform parameter on line 2")):
        asm.assemble()


def test_matmul4x4_invalid_matrix_uniform_type():
    asm = Assembler("#test_matrix vector 14\n" "%matmul4x4 r0 iPos #test_matrix")
    with pytest.raises(ValueError, match=re.escape("Invalid matrix uniform type on line 2")):
        asm.assemble()


def test_matmul4x4_invalid_matrix_uniform_offset():
    asm = Assembler("#test_matrix matrix4 14\n" "%matmul4x4 r0 iPos #test_matrix[1]")
    with pytest.raises(ValueError, match=re.escape("Invalid matrix uniform offset on line 2")):
        asm.assemble()


def test_matmul4x4_valid():
    asm = Assembler("#test_matrix matrix4 14\n" "%matmul4x4 r0 iPos #test_matrix")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 5
    _assert_program(
        [
            [0, 14794779, 137762924, 671092728],
            [0, 14802971, 137762924, 603983864],
            [0, 14811163, 137762924, 570429432],
            [0, 14819355, 137762924, 553652216],
        ],
        results,
    )


def test_matmul4x4_valid_with_following_instruction():
    asm = Assembler("#test_matrix matrix4 14\n" "%matmul4x4 r0 iPos #test_matrix\n" "mov r1, r0")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 6
    _assert_program(
        [
            [0, 14794779, 137762924, 671092728],
            [0, 14802971, 137762924, 603983864],
            [0, 14811163, 137762924, 570429432],
            [0, 14819355, 137762924, 553652216],
            [0, 2097179, 70652012, 789581816],
        ],
        results,
    )


def test_paired():
    asm = Assembler("MUL R2.xyzw, R1, c[0] + MOV oD1.xyzw, v4")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 2
    _assert_vsh([0x00000000, 0x0240081B, 0x1436186C, 0x2F20F824], results[0])


def test_arl():
    asm = Assembler("ARL A0, R0.x")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 2
    _assert_vsh([0x00000000, 0x01A00000, 0x0436106C, 0x20700FF8], results[0])
    # Ambiguous result, it looks like some compilers null out unused fields
    # differently.
    # _assert_vsh([0x00000000, 0x01A00000, 0x04001000, 0x20000000], results[0])


def test_rcp():
    asm = Assembler("RCP oFog, v0.w")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 2
    _assert_vsh([0x00000000, 0x0400001B, 0x083613FC, 0x2070F82C], results[0])


def test_r12():
    asm = Assembler("MUL oPos.xyz, R12.xyz, c[58].xyz")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 2
    _assert_vsh([0x00000000, 0x0047401A, 0xC434186C, 0x2070E800], results[0])
    # Ambiguous result, differs in unused fields.
    # _assert_vsh([0x00000000, 0x0047401A, 0xC4355800, 0x20A0E800], results[0])


def test_two_output_instruction():
    asm = Assembler("DP4 oPos.z, R6, c[98] + DP4 R0.x, R6, c[98]")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 2
    _assert_vsh([0x00000000, 0x00EC401B, 0x6436186C, 0x28002800], results[0])
    # Ambiguous result, differs in unused fields.
    # _assert_vsh([0x00000000, 0x00EC401B, 0x64365800, 0x28002800], results[0])


def test_paired_ilu_non_r1_temporary_writes_to_r1():
    asm = Assembler("DP4 oPos.x, R6, c[96] + RSQ R10.x, R2.x")
    asm.assemble()
    results = asm.output
    _assert_final_marker(results)
    assert len(results) == 2
    _assert_vsh([0x00000000, 0x08EC001B, 0x64361800, 0x90188800], results[0])


def test_simple():
    all_input = os.path.join(_RESOURCE_PATH, "simple.vsh")
    with open(all_input) as infile:
        source = infile.read()

    asm = Assembler(source)
    asm.assemble(inline_final_flag=True)
    results = asm.output

    expected_instructions = _extract_expected_instructions(source)
    assert len(results) == len(expected_instructions)
    for expected, actual in zip(expected_instructions, results):
        _assert_vsh(expected, actual)


def test_ngb_lava():
    all_input = os.path.join(_RESOURCE_PATH, "ngb_lava.vsh")
    with open(all_input) as infile:
        source = infile.read()

    asm = Assembler(source)
    asm.assemble(inline_final_flag=True)
    results = asm.output

    expected_instructions = _extract_expected_instructions(source)
    assert len(results) == len(expected_instructions)
    for expected, actual in zip(expected_instructions, results):
        _assert_vsh(expected, actual)


def test_trivial_end_to_end_shader():
    all_input = os.path.join(_RESOURCE_PATH, "set_pos_and_color.vsh")
    with open(all_input) as infile:
        source = infile.read()

    asm = Assembler(source)
    asm.assemble(inline_final_flag=True)
    results = asm.output

    expected_instructions = _extract_expected_instructions(source)
    assert len(results) == len(expected_instructions)
    for expected, actual in zip(expected_instructions, results):
        _assert_vsh(expected, actual)


def _assert_final_marker(results):
    assert [0, 0, 0, 1], results[-1]


def _assert_vsh(expected: list[int], actual: list[int]):
    diff = vsh_instruction.vsh_diff_instructions(expected, actual)
    assert not diff


def _assert_program(expected: list[list[int]], actual: list[list[int]]):
    # Assume that the terminator was checked via assert final marker
    for i, actual_line in enumerate(actual):
        if i == len(expected):
            assert actual_line == [0, 0, 0, 1], "Actual data is longer than expected"
            return
        _assert_vsh(expected[i], actual_line)
