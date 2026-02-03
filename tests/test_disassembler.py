"""Tests for disassembler functionality."""

# ruff: noqa: SLF001 Private member accessed

# pylint: disable=missing-function-docstring
# pylint: disable=protected-access
# pylint: disable=too-many-public-methods
# pylint: disable=wrong-import-order

from __future__ import annotations

import io

import pytest

from nv2a_vsh import disassemble


def test_text_input_parser_empty() -> None:
    test = io.StringIO("")
    result = disassemble._parse_text_input(test)
    assert result == []


def test_text_input_parser_valid_single_line_one_instruction() -> None:
    test = io.StringIO("0x0,0x1,0x2,0x3")
    result = disassemble._parse_text_input(test)
    assert result == [[0, 1, 2, 3]]


def test_text_input_parser_valid_multiple_lines_one_instruction() -> None:
    test = io.StringIO("0x0,0x1,\n\t0x2,   0x3  ")
    result = disassemble._parse_text_input(test)
    assert result == [[0, 1, 2, 3]]


def test_text_input_parser_valid_single_line_multiple_instructions() -> None:
    test = io.StringIO("0x0,0x1,0x2,0x3")
    result = disassemble._parse_text_input(test)
    assert result == [[0, 1, 2, 3]]


def test_text_input_parser_valid_multiple_lines_multiple_instructions() -> None:
    test = io.StringIO("0x0,0x1,0x2,0x3")
    result = disassemble._parse_text_input(test)
    assert result == [[0, 1, 2, 3]]


def test_disassembler_empty() -> None:
    test: list[list[int]] = []
    result = disassemble.disassemble(test, explain=False)
    assert result == []


def test_disassembler_explicit_nop() -> None:
    test: list[list[int]] = [[0, 0, 0, 0]]
    result = disassemble.disassemble(test, explain=False)
    assert result == ["/* 0, 0, 0, 0 */"]


@pytest.mark.parametrize(
    ("expected", "value"),
    [
        ("MOV oT2.xyzw, v11", [0x00000000, 0x0020161B, 0x0836106C, 0x2070F858]),
        (
            "MAD oPos.xyz, R12, R1.x, c[59]",
            [0x00000000, 0x0087601B, 0xC400286C, 0x3070E801],
        ),
        ("DP4 oPos.z, v0, c[100]", [0x00000000, 0x00EC801B, 0x0836186C, 0x20702800]),
        # This is an ambiguous pair, there are differences in unused mappings.
        (
            "MAD R0.z, R0.z, c[117].z, -c[117].w",
            [0x00000000, 0x008EA0AA, 0x05541FFC, 0x32000FF8],
        ),
        (
            "MAD R0.z, R0.z, c[117].z, -c[117].w",
            [0x00000000, 0x008EA0AA, 0x0554BFFD, 0x72000000],
        ),
        ("ARL A0, R0.x", [0x00000000, 0x01A00000, 0x0436106C, 0x20700FF8]),
        (
            "ADD R0.xy, c[A0+121].zw, -c[A0+121].xy",
            [0x00000000, 0x006F20BF, 0x9C001456, 0x7C000002],
        ),
        (
            "RCP oFog.xyzw, v0.w",
            [0x00000000, 0x0400001B, 0x083613FC, 0x2070F82C],
        ),
        (
            "MUL oPos.xyz, R12.xyz, c[58].xyz",
            [0x00000000, 0x0047401A, 0xC434186C, 0x2070E800],
        ),
    ],
)
def test_disassembler_single_no_explain(expected: str, value: list[int]) -> None:
    assert [expected] == disassemble.disassemble([value], explain=False)


def test_disassembler_paired_no_explain() -> None:
    def _test(expected, value):
        result = disassemble.disassemble([value], explain=False)
        assert [expected] == result

    _test(
        "MUL R2.xyzw, R1, c[0] + MOV oD1.xyzw, v4",
        [0x00000000, 0x0240081B, 0x1436186C, 0x2F20F824],
    )

    _test(
        "MOV oD0.xyzw, v3 + RCP R1.w, R1.w",
        [0x00000000, 0x0420061B, 0x083613FC, 0x5011F818],
    )

    _test(
        "DP4 oPos.x, R6, c[96] + RSQ R1.x, R2.x",
        [0x00000000, 0x08EC001B, 0x64361800, 0x90A88800],
    )


@pytest.mark.parametrize(
    ("expected", "value"),
    [
        (
            "DP4 oPos.z, R6, c[98] + DP4 R0.x, R6, c[98]",
            [0x00000000, 0x00EC401B, 0x64365800, 0x28002800],
        ),
        (
            "MAD oPos.xyz, R12.xyz, R1.x, c[1].xyz + MAD R11.xy, R12.xyz, R1.x, c[1].xyz",
            [0x00000000, 0x0080201A, 0xC4002868, 0x3CB0E800],
        ),
        (
            "ADD oPos.xyz, R12, v4 + ADD R0.xyz, R12, v4",
            [0x00000000, 0x0060081B, 0xC436106C, 0x2E00E800],
        ),
        (
            "RCP oPos.x, R12.x + RCP R1.x, R12.x",
            [0x00000000, 0x400001B, 0x08361003, 0x10188804],
        ),
        (
            "MOV R0.x, R12.x + RCP oPos.x, R12.x + RCP R1.x, R12.x",
            [0x00000000, 0x04200000, 0xC4361003, 0x18088804],
        ),
    ],
)
def test_disassembler_multi_output_no_explain(expected: str, value: list[int]) -> None:
    assert disassemble.disassemble([value], explain=False) == [expected]


def test_disassembler_constant_register_output_no_explain() -> None:
    def _test(expected, value):
        result = disassemble.disassemble([value], explain=False)
        assert [expected] == result

    _test(
        "DPH c[15].xy, v4, c[10]",
        [0x00000000, 0x00C1481B, 0x0836186C, 0x2070C078],
    )
