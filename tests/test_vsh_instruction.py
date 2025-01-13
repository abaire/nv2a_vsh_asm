from __future__ import annotations

import re

import pytest

from nv2a_vsh.nv2a_vsh_asm.vsh_instruction import VshInstruction, explain, vsh_diff_instructions


def test_default_explain():
    instruction = VshInstruction()
    assert instruction.explain() == (
        "0x00000000, 0x0000001B, 0x0836106C, 0x20700FF8:\n"
        "\tA_SWZ_W: 0x3 (11)\n"
        "\tA_SWZ_Z: 0x2 (10)\n"
        "\tA_SWZ_Y: 0x1 (01)\n"
        "\tA_SWZ_X: 0x0 (00)\n"
        "\tA_NEG: 0x0 (0)\n"
        "\tINPUT: 0x0 (0000)\n"
        "\tCONST: 0x0 (00000000)\n"
        "\tMAC: 0x0 (0000)\n"
        "\tILU: 0x0 (000)\n"
        "\tC_TEMP_REG_HIGH: 0x0 (00)\n"
        "\tC_SWZ_W: 0x3 (11)\n"
        "\tC_SWZ_Z: 0x2 (10)\n"
        "\tC_SWZ_Y: 0x1 (01)\n"
        "\tC_SWZ_X: 0x0 (00)\n"
        "\tC_NEG: 0x0 (0)\n"
        "\tB_MUX: 0x2 (10)\n"
        "\tB_TEMP_REG: 0x0 (0000)\n"
        "\tB_SWZ_W: 0x3 (11)\n"
        "\tB_SWZ_Z: 0x2 (10)\n"
        "\tB_SWZ_Y: 0x1 (01)\n"
        "\tB_SWZ_X: 0x0 (00)\n"
        "\tB_NEG: 0x0 (0)\n"
        "\tA_MUX: 0x2 (10)\n"
        "\tA_TEMP_REG: 0x0 (0000)\n"
        "\tFINAL: 0x0 (0)\n"
        "\tA0X: 0x0 (0)\n"
        "\tOUT_MUX: 0x0 (0)\n"
        "\tOUT_ADDRESS: 0xff (11111111)\n"
        "\tOUT_ORB: 0x1 (1)\n"
        "\tOUT_O_MASK: 0x0 (0000)\n"
        "\tOUT_ILU_MASK: 0x0 (0000)\n"
        "\tOUT_TEMP_REG: 0x7 (0111)\n"
        "\tOUT_MAC_MASK: 0x0 (0000)\n"
        "\tC_MUX: 0x2 (10)\n"
        "\tC_TEMP_REG_LOW: 0x0 (00)"
    )


@pytest.mark.parametrize(
    "data",
    [
        [],
        ["test"],
        [0x0],
        [0, 1, 2],
    ],
)
def test_explain_with_invalid_input(data):
    with pytest.raises(ValueError, match=re.escape(f"set_values must be exactly 4 elements but was {data!r}")):
        explain(data)


def test_explain_with_invalid_first_opcode():
    with pytest.raises(ValueError, match=re.escape("First element must be zero [1, 2, 3, 4]")):
        explain([1, 2, 3, 4])


def test_explain_with_default_opcode():
    assert explain([0, 0, 0, 0]) == (
        "0x00000000, 0x00000000, 0x00000000, 0x00000000:\n"
        "\tA_SWZ_W: 0x0 (00)\n"
        "\tA_SWZ_Z: 0x0 (00)\n"
        "\tA_SWZ_Y: 0x0 (00)\n"
        "\tA_SWZ_X: 0x0 (00)\n"
        "\tA_NEG: 0x0 (0)\n"
        "\tINPUT: 0x0 (0000)\n"
        "\tCONST: 0x0 (00000000)\n"
        "\tMAC: 0x0 (0000)\n"
        "\tILU: 0x0 (000)\n"
        "\tC_TEMP_REG_HIGH: 0x0 (00)\n"
        "\tC_SWZ_W: 0x0 (00)\n"
        "\tC_SWZ_Z: 0x0 (00)\n"
        "\tC_SWZ_Y: 0x0 (00)\n"
        "\tC_SWZ_X: 0x0 (00)\n"
        "\tC_NEG: 0x0 (0)\n"
        "\tB_MUX: 0x0 (00)\n"
        "\tB_TEMP_REG: 0x0 (0000)\n"
        "\tB_SWZ_W: 0x0 (00)\n"
        "\tB_SWZ_Z: 0x0 (00)\n"
        "\tB_SWZ_Y: 0x0 (00)\n"
        "\tB_SWZ_X: 0x0 (00)\n"
        "\tB_NEG: 0x0 (0)\n"
        "\tA_MUX: 0x0 (00)\n"
        "\tA_TEMP_REG: 0x0 (0000)\n"
        "\tFINAL: 0x0 (0)\n"
        "\tA0X: 0x0 (0)\n"
        "\tOUT_MUX: 0x0 (0)\n"
        "\tOUT_ADDRESS: 0x0 (00000000)\n"
        "\tOUT_ORB: 0x0 (0)\n"
        "\tOUT_O_MASK: 0x0 (0000)\n"
        "\tOUT_ILU_MASK: 0x0 (0000)\n"
        "\tOUT_TEMP_REG: 0x0 (0000)\n"
        "\tOUT_MAC_MASK: 0x0 (0000)\n"
        "\tC_MUX: 0x0 (00)\n"
        "\tC_TEMP_REG_LOW: 0x0 (00)"
    )


@pytest.mark.parametrize(
    "data",
    [
        [],
        ["test"],
        [0x0],
        [0, 1, 2],
    ],
)
def test_diff_instructions_invalid_expected(data):
    with pytest.raises(ValueError, match=re.escape(f"expected {data!r} must be a 4-integer encoded instruction")):
        vsh_diff_instructions(data, [0x0, 0x0, 0x0, 0x0], ignore_final_flag=False)


@pytest.mark.parametrize(
    "data",
    [
        [],
        ["test"],
        [0x0],
        [0, 1, 2],
    ],
)
def test_diff_instructions_invalid_actual(data):
    with pytest.raises(ValueError, match=re.escape(f"actual {data!r} must be a 4-integer encoded instruction")):
        vsh_diff_instructions([0x0, 0x0, 0x0, 0x0], data, ignore_final_flag=False)


def test_diff_instructions_bad_first_value():
    with pytest.raises(ValueError, match=re.escape("First value in expected [1, 0, 0, 0] must be 0")):
        vsh_diff_instructions([0x1, 0x0, 0x0, 0x0], [0x0, 0x0, 0x0, 0x0], ignore_final_flag=False)


@pytest.mark.parametrize(
    ("expected", "actual", "ignore_final_flag"),
    [
        ([0x0, 0x0, 0x0, 0x0], [0x0, 0x0, 0x0, 0x0], True),
        ([0x0, 0x0, 0x0, 0x1], [0x0, 0x0, 0x0, 0x0], True),
        ([0x0, 0x0, 0x0, 0x1], [0x0, 0x0, 0x0, 0x1], True),
        ([0x0, 0x0, 0x0, 0x1], [0x0, 0x0, 0x0, 0x1], False),
    ],
)
def test_diff_instructions_equivalent(expected: list[int], actual: list[int], *, ignore_final_flag: bool):
    assert vsh_diff_instructions(expected, actual, ignore_final_flag=ignore_final_flag) == ""


def test_diff_instructions_different_final_flag():
    assert (
        vsh_diff_instructions([0x0, 0x0, 0x0, 0x1], [0x0, 0x0, 0x0, 0x0], ignore_final_flag=False)
        == "Instructions differ.\n\t0x00000000 0x00000000 0x00000000 0x00000001\n\t0x00000000 0x00000000 0x00000000 0x00000000\n\n\tFINAL 0x1 (1) != actual 0x0 (0)\n"
    )


def test_diff_instructions_different_first_value():
    assert (
        vsh_diff_instructions([0x0, 0x0, 0x0, 0x0], [0x1, 0x0, 0x0, 0x0], ignore_final_flag=False)
        == "Instructions differ.\n\t0x00000000 0x00000000 0x00000000 0x00000000\n\t0x00000001 0x00000000 0x00000000 0x00000000\n\n\tInvalid instruction, [0](0x00000001) must == 0\n"
    )


def test_diff_instructions_different_b_fields_differ():
    assert (
        vsh_diff_instructions([0x0, 0x0, 0x0, 0x0], [0x0, 0x1, 0x0, 0x0], ignore_final_flag=False)
        == "Instructions differ.\n\t0x00000000 0x00000000 0x00000000 0x00000000\n\t0x00000000 0x00000001 0x00000000 0x00000000\n\n\tA_SWZ_W 0x0 (00) != actual 0x1 (01)\n"
    )


def test_diff_instructions_different_c_fields_differ():
    assert (
        vsh_diff_instructions([0x0, 0x0, 0x0, 0x0], [0x0, 0x0, 0x1, 0x0], ignore_final_flag=False)
        == "Instructions differ.\n\t0x00000000 0x00000000 0x00000000 0x00000000\n\t0x00000000 0x00000000 0x00000001 0x00000000\n\n\tC_TEMP_REG_HIGH 0x0 (00) != actual 0x1 (01)\n"
    )
