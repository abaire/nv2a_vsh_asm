"""Provides functionality for manipulating nv2a vertex shader machine code."""

# pylint: disable=invalid-name
# pylint: disable=missing-function-docstring
# pylint: disable=protected-access
# pylint: disable=too-few-public-methods
# pylint: disable=too-many-arguments
# pylint: disable=too-many-branches
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-public-methods
# pylint: disable=unused-wildcard-import
# pylint: disable=wildcard-import

import ctypes
import itertools
import struct
import sys
from typing import List, Tuple

from .vsh_encoder_defs import *


class _B(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("A_SWZ_W", ctypes.c_uint32, 2),
        ("A_SWZ_Z", ctypes.c_uint32, 2),
        ("A_SWZ_Y", ctypes.c_uint32, 2),
        ("A_SWZ_X", ctypes.c_uint32, 2),
        ("A_NEG", ctypes.c_uint32, 1),
        ("INPUT", ctypes.c_uint32, 4),
        ("CONST", ctypes.c_uint32, 8),
        ("MAC", ctypes.c_uint32, 4),
        ("ILU", ctypes.c_uint32, 3),
    ]


class _C(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("C_TEMP_REG_HIGH", ctypes.c_uint32, 2),
        ("C_SWZ_W", ctypes.c_uint32, 2),
        ("C_SWZ_Z", ctypes.c_uint32, 2),
        ("C_SWZ_Y", ctypes.c_uint32, 2),
        ("C_SWZ_X", ctypes.c_uint32, 2),
        ("C_NEG", ctypes.c_uint32, 1),
        ("B_MUX", ctypes.c_uint32, 2),
        ("B_TEMP_REG", ctypes.c_uint32, 4),
        ("B_SWZ_W", ctypes.c_uint32, 2),
        ("B_SWZ_Z", ctypes.c_uint32, 2),
        ("B_SWZ_Y", ctypes.c_uint32, 2),
        ("B_SWZ_X", ctypes.c_uint32, 2),
        ("B_NEG", ctypes.c_uint32, 1),
        ("A_MUX", ctypes.c_uint32, 2),
        ("A_TEMP_REG", ctypes.c_uint32, 4),
    ]


class _D(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("FINAL", ctypes.c_uint32, 1),
        ("A0X", ctypes.c_uint32, 1),
        ("OUT_MUX", ctypes.c_uint32, 1),
        ("OUT_ADDRESS", ctypes.c_uint32, 8),
        ("OUT_ORB", ctypes.c_uint32, 1),
        ("OUT_O_MASK", ctypes.c_uint32, 4),
        ("OUT_ILU_MASK", ctypes.c_uint32, 4),
        ("OUT_TEMP_REG", ctypes.c_uint32, 4),
        ("OUT_MAC_MASK", ctypes.c_uint32, 4),
        ("C_MUX", ctypes.c_uint32, 2),
        ("C_TEMP_REG_LOW", ctypes.c_uint32, 2),
    ]


def get_swizzle(swz: int, idx: int) -> int:
    """Extracts the swizzle component at `idx` from `swz`."""
    return ((swz) >> ((idx) * 3)) & 0x7


_VSH_MASK_TO_WRITEMASK = {
    MASK_X: WRITEMASK_X,
    MASK_Y: WRITEMASK_Y,
    MASK_XY: WRITEMASK_XY,
    MASK_Z: WRITEMASK_Z,
    MASK_XZ: WRITEMASK_XZ,
    MASK_YZ: WRITEMASK_YZ,
    MASK_XYZ: WRITEMASK_XYZ,
    MASK_W: WRITEMASK_W,
    MASK_XW: WRITEMASK_XW,
    MASK_YW: WRITEMASK_YW,
    MASK_XYW: WRITEMASK_XYW,
    MASK_ZW: WRITEMASK_ZW,
    MASK_XZW: WRITEMASK_XZW,
    MASK_YZW: WRITEMASK_YZW,
    MASK_XYZW: WRITEMASK_XYZW,
}

_SWIZZLE_NAME = {
    SWIZZLE_X: "x",
    SWIZZLE_Y: "y",
    SWIZZLE_Z: "z",
    SWIZZLE_W: "w",
}


def _make_swizzle_name(x: int, y: int, z: int, w: int, suppress_nop=False) -> str:
    # Drop any repeated elements at the end of the list.
    components = [group[0] for group in itertools.groupby([x, y, z, w])]

    ret = "".join([_SWIZZLE_NAME[i] for i in components])

    if suppress_nop and ret == "xyzw":
        return ""
    return ret


def get_swizzle_name(swizzle: int) -> str:
    """Returns the textual name for the given swizzle."""
    ret = ""
    for i in range(4):
        ret += _SWIZZLE_NAME[get_swizzle(swizzle, i)]
    return ret


class VshInstruction:
    """Models nv2a vertex shader machine code."""

    def __init__(self, empty_final=False):
        self._b: _B
        self._c: _C
        self._d: _D
        self._set_empty()

        if empty_final:
            self.final = True
        else:
            self.ilu = ILU.ILU_NOP
            self.mac = MAC.MAC_NOP

            self.a_swizzle_x = SWIZZLE_X
            self.a_swizzle_y = SWIZZLE_Y
            self.a_swizzle_z = SWIZZLE_Z
            self.a_swizzle_w = SWIZZLE_W
            self.a_mux = PARAM_V

            self.b_swizzle_x = SWIZZLE_X
            self.b_swizzle_y = SWIZZLE_Y
            self.b_swizzle_z = SWIZZLE_Z
            self.b_swizzle_w = SWIZZLE_W
            self.b_mux = PARAM_V

            self.c_swizzle_x = SWIZZLE_X
            self.c_swizzle_y = SWIZZLE_Y
            self.c_swizzle_z = SWIZZLE_Z
            self.c_swizzle_w = SWIZZLE_W
            self.c_mux = PARAM_V

            self.out_temp_reg = 7
            self.out_address = 0xFF
            self.out_mux = OMUX_MAC
            self.out_o_or_c = OUTPUT_O

    def _set_empty(self):
        zero = bytes(b"\0" * 4)
        self._b = _B.from_buffer_copy(zero)
        self._c = _C.from_buffer_copy(zero)
        self._d = _D.from_buffer_copy(zero)

    def set_empty_final(self):
        """Sets this instruction to a NOP with the FINAL flag set."""
        self._set_empty()
        self.final = True

    def set_values(self, values: List[int]):
        """Sets the raw values for this instruction."""
        assert len(values) == 4
        assert values[0] == 0

        self._b = _B.from_buffer_copy(values[1].to_bytes(4, byteorder=sys.byteorder))
        self._c = _C.from_buffer_copy(values[2].to_bytes(4, byteorder=sys.byteorder))
        self._d = _D.from_buffer_copy(values[3].to_bytes(4, byteorder=sys.byteorder))

    @property
    def a_swizzle_w(self) -> int:
        return self._b.A_SWZ_W

    @a_swizzle_w.setter
    def a_swizzle_w(self, val: int):
        self._b.A_SWZ_W = val

    @property
    def a_swizzle_z(self) -> int:
        return self._b.A_SWZ_Z

    @a_swizzle_z.setter
    def a_swizzle_z(self, val: int):
        self._b.A_SWZ_Z = val

    @property
    def a_swizzle_y(self) -> int:
        return self._b.A_SWZ_Y

    @a_swizzle_y.setter
    def a_swizzle_y(self, val: int):
        self._b.A_SWZ_Y = val

    @property
    def a_swizzle_x(self) -> int:
        return self._b.A_SWZ_X

    @a_swizzle_x.setter
    def a_swizzle_x(self, val: int):
        self._b.A_SWZ_X = val

    @property
    def a_negate(self) -> bool:
        return bool(self._b.A_NEG)

    @a_negate.setter
    def a_negate(self, val: bool):
        if val:
            self._b.A_NEG = 1
        else:
            self._b.A_NEG = 0

    @property
    def input_reg(self) -> int:
        return self._b.INPUT

    @input_reg.setter
    def input_reg(self, val: int):
        self._b.INPUT = val

    @property
    def const_reg(self) -> int:
        return self._b.CONST

    @const_reg.setter
    def const_reg(self, val: int):
        self._b.CONST = val

    @property
    def mac(self) -> int:
        return self._b.MAC

    @mac.setter
    def mac(self, val: int):
        self._b.MAC = val

    @property
    def ilu(self) -> int:
        return self._b.ILU

    @ilu.setter
    def ilu(self, val: int):
        self._b.ILU = val

    @property
    def c_temp_reg(self) -> int:
        ret = (self.c_temp_reg_high & 0x03) << 2
        ret += self.c_temp_reg_low & 0x03
        return ret

    @c_temp_reg.setter
    def c_temp_reg(self, val: int):
        self.c_temp_reg_low = val & 0x03
        self.c_temp_reg_high = (val >> 2) & 0x03

    @property
    def c_temp_reg_high(self) -> int:
        return self._c.C_TEMP_REG_HIGH

    @c_temp_reg_high.setter
    def c_temp_reg_high(self, val: int):
        self._c.C_TEMP_REG_HIGH = val

    @property
    def c_swizzle_w(self) -> int:
        return self._c.C_SWZ_W

    @c_swizzle_w.setter
    def c_swizzle_w(self, val: int):
        self._c.C_SWZ_W = val

    @property
    def c_swizzle_z(self) -> int:
        return self._c.C_SWZ_Z

    @c_swizzle_z.setter
    def c_swizzle_z(self, val: int):
        self._c.C_SWZ_Z = val

    @property
    def c_swizzle_y(self) -> int:
        return self._c.C_SWZ_Y

    @c_swizzle_y.setter
    def c_swizzle_y(self, val: int):
        self._c.C_SWZ_Y = val

    @property
    def c_swizzle_x(self) -> int:
        return self._c.C_SWZ_X

    @c_swizzle_x.setter
    def c_swizzle_x(self, val: int):
        self._c.C_SWZ_X = val

    @property
    def c_negate(self) -> bool:
        return bool(self._c.C_NEG)

    @c_negate.setter
    def c_negate(self, val: bool):
        if val:
            self._c.C_NEG = 1
        else:
            self._c.C_NEG = 0

    @property
    def b_mux(self) -> int:
        return self._c.B_MUX

    @b_mux.setter
    def b_mux(self, val: int):
        self._c.B_MUX = val

    @property
    def b_temp_reg(self) -> int:
        return self._c.B_TEMP_REG

    @b_temp_reg.setter
    def b_temp_reg(self, val: int):
        self._c.B_TEMP_REG = val

    @property
    def b_swizzle_w(self) -> int:
        return self._c.B_SWZ_W

    @b_swizzle_w.setter
    def b_swizzle_w(self, val: int):
        self._c.B_SWZ_W = val

    @property
    def b_swizzle_z(self) -> int:
        return self._c.B_SWZ_Z

    @b_swizzle_z.setter
    def b_swizzle_z(self, val: int):
        self._c.B_SWZ_Z = val

    @property
    def b_swizzle_y(self) -> int:
        return self._c.B_SWZ_Y

    @b_swizzle_y.setter
    def b_swizzle_y(self, val: int):
        self._c.B_SWZ_Y = val

    @property
    def b_swizzle_x(self) -> int:
        return self._c.B_SWZ_X

    @b_swizzle_x.setter
    def b_swizzle_x(self, val: int):
        self._c.B_SWZ_X = val

    @property
    def b_negate(self) -> bool:
        return bool(self._c.B_NEG)

    @b_negate.setter
    def b_negate(self, val: bool):
        if val:
            self._c.B_NEG = 1
        else:
            self._c.B_NEG = 0

    @property
    def a_mux(self) -> int:
        return self._c.A_MUX

    @a_mux.setter
    def a_mux(self, val: int):
        self._c.A_MUX = val

    @property
    def a_temp_reg(self) -> int:
        return self._c.A_TEMP_REG

    @a_temp_reg.setter
    def a_temp_reg(self, val: int):
        self._c.A_TEMP_REG = val

    @property
    def final(self) -> bool:
        return bool(self._d.FINAL)

    @final.setter
    def final(self, val: bool):
        if val:
            self._d.FINAL = 1
        else:
            self._d.FINAL = 0

    @property
    def a0x(self) -> bool:
        return bool(self._d.A0X)

    @a0x.setter
    def a0x(self, val: bool):
        if val:
            self._d.A0X = 1
        else:
            self._d.A0X = 0

    @property
    def out_mux(self) -> bool:
        return bool(self._d.OUT_MUX)

    @out_mux.setter
    def out_mux(self, val: bool):
        if val:
            self._d.OUT_MUX = 1
        else:
            self._d.OUT_MUX = 0

    @property
    def out_address(self) -> int:
        return self._d.OUT_ADDRESS

    @out_address.setter
    def out_address(self, val: int):
        self._d.OUT_ADDRESS = val

    @property
    def out_o_or_c(self) -> bool:
        return bool(self._d.OUT_ORB)

    # This switches output address being treated as an output register or a constant
    # OUTPUT_O or OUTPUT_C
    @out_o_or_c.setter
    def out_o_or_c(self, val: bool):
        if val:
            self._d.OUT_ORB = 1
        else:
            self._d.OUT_ORB = 0

    @property
    def out_o_mask(self) -> int:
        return self._d.OUT_O_MASK

    @out_o_mask.setter
    def out_o_mask(self, val: int):
        self._d.OUT_O_MASK = val

    @property
    def out_ilu_mask(self) -> int:
        return self._d.OUT_ILU_MASK

    @out_ilu_mask.setter
    def out_ilu_mask(self, val: int):
        self._d.OUT_ILU_MASK = val

    @property
    def out_temp_reg(self) -> int:
        return self._d.OUT_TEMP_REG

    @out_temp_reg.setter
    def out_temp_reg(self, val: int):
        self._d.OUT_TEMP_REG = val

    @property
    def out_mac_mask(self) -> int:
        return self._d.OUT_MAC_MASK

    @out_mac_mask.setter
    def out_mac_mask(self, val: int):
        self._d.OUT_MAC_MASK = val

    @property
    def c_mux(self) -> int:
        return self._d.C_MUX

    @c_mux.setter
    def c_mux(self, val: int):
        self._d.C_MUX = val

    @property
    def c_temp_reg_low(self) -> int:
        return self._d.C_TEMP_REG_LOW

    @c_temp_reg_low.setter
    def c_temp_reg_low(self, val: int):
        self._d.C_TEMP_REG_LOW = val

    def encode(self) -> List[int]:
        """Encodes this instruction into a machine code quadruplet."""
        a = 0
        b = struct.unpack("<L", self._b)[0]
        c = struct.unpack("<L", self._c)[0]
        d = struct.unpack("<L", self._d)[0]

        return [a, b, c, d]

    def set_mux_field(self, src_index: int, val: int):
        """Sets the mux field for the given src_index."""
        if src_index == 0:
            self.a_mux = val
        elif src_index == 1:
            self.b_mux = val
        elif src_index == 2:
            self.c_mux = val
        else:
            raise Exception(f"Invalid field index {src_index}")

    def set_temp_reg_field(self, src_index: int, val: int):
        """Sets the temp register access for the given src_index."""
        if src_index == 0:
            self.a_temp_reg = val
        elif src_index == 1:
            self.b_temp_reg = val
        elif src_index == 2:
            self.c_temp_reg = val
        else:
            raise Exception(f"Invalid field index {src_index}")

    def set_negate_field(self, src_index: int, val: bool):
        """Sets the negate field for the given src_index."""
        if src_index == 0:
            self.a_negate = val
        elif src_index == 1:
            self.b_negate = val
        elif src_index == 2:
            self.c_negate = val
        else:
            raise Exception(f"Invalid field index {src_index}")

    def set_swizzle_fields(self, src_index: int, swizzle: int):
        """Sets the swizzle fields for the given src_index."""
        if src_index == 0:
            self.a_swizzle_x = get_swizzle(swizzle, 0)
            self.a_swizzle_y = get_swizzle(swizzle, 1)
            self.a_swizzle_z = get_swizzle(swizzle, 2)
            self.a_swizzle_w = get_swizzle(swizzle, 3)
        elif src_index == 1:
            self.b_swizzle_x = get_swizzle(swizzle, 0)
            self.b_swizzle_y = get_swizzle(swizzle, 1)
            self.b_swizzle_z = get_swizzle(swizzle, 2)
            self.b_swizzle_w = get_swizzle(swizzle, 3)
        elif src_index == 2:
            self.c_swizzle_x = get_swizzle(swizzle, 0)
            self.c_swizzle_y = get_swizzle(swizzle, 1)
            self.c_swizzle_z = get_swizzle(swizzle, 2)
            self.c_swizzle_w = get_swizzle(swizzle, 3)
        else:
            raise Exception(f"Invalid field index {src_index}")

    def _dissasemble_inputs(self) -> List[str]:
        def _process(mux, negate, temp_reg, x, y, z, w):
            if mux == PARAM_R:
                ret = f"R{temp_reg}"
            elif mux == PARAM_C:
                offset = f"{self.const_reg}"
                if self.a0x:
                    offset = f"A0+{offset}"
                ret = f"c[{offset}]"
            elif mux == PARAM_V:
                ret = f"v{self.input_reg}"
            else:
                raise Exception(f"Unknown mux code {mux}")
            if negate:
                ret = f"-{ret}"

            swizzle = _make_swizzle_name(x, y, z, w, True)
            if swizzle:
                ret += f".{swizzle}"
            return ret

        src_a = _process(
            self.a_mux,
            self.a_negate,
            self.a_temp_reg,
            self.a_swizzle_x,
            self.a_swizzle_y,
            self.a_swizzle_z,
            self.a_swizzle_w,
        )
        src_b = _process(
            self.b_mux,
            self.b_negate,
            self.b_temp_reg,
            self.b_swizzle_x,
            self.b_swizzle_y,
            self.b_swizzle_z,
            self.b_swizzle_w,
        )
        src_c = _process(
            self.c_mux,
            self.c_negate,
            self.c_temp_reg,
            self.c_swizzle_x,
            self.c_swizzle_y,
            self.c_swizzle_z,
            self.c_swizzle_w,
        )

        return [src_a, src_b, src_c]

    def _disassemble_outputs(self) -> Tuple[List[str], List[str]]:
        """Returns a pair of lists of destination strings for (mac, ilu)."""

        mac_temp_destination = ""
        ilu_temp_destination = ""
        dst_temp_reg_name = f"R{self.out_temp_reg}"
        if self.out_mac_mask:
            mac_output_mask = WRITEMASK_NAME[_VSH_MASK_TO_WRITEMASK[self.out_mac_mask]]
            if not mac_output_mask:
                mac_output_mask = ".xyzw"
            mac_temp_destination = f"{dst_temp_reg_name}{mac_output_mask}"

        if self.out_ilu_mask:
            ilu_output_mask = WRITEMASK_NAME[_VSH_MASK_TO_WRITEMASK[self.out_ilu_mask]]
            if not ilu_output_mask:
                ilu_output_mask = ".xyzw"

            # If this is a paired ILU instruction, ILU will write to R1 regardless of
            # the encoded target.
            if self.mac:
                ilu_temp_destination = f"R1{ilu_output_mask}"
            else:
                ilu_temp_destination = f"{dst_temp_reg_name}{ilu_output_mask}"

        mac = []
        ilu = []

        if self.out_o_mask:
            dst_output_mask = WRITEMASK_NAME[_VSH_MASK_TO_WRITEMASK[self.out_o_mask]]
            if not dst_output_mask:
                dst_output_mask = ".xyzw"
            dst_output_index = self.out_address

            if self.out_o_or_c == OUTPUT_O:
                dst_output_name = DESTINATION_REGISTER_TO_NAME_MAP_SHORT[
                    dst_output_index
                ]
            else:
                dst_output_name = f"c[{dst_output_index}]"

            out_destination = f"{dst_output_name}{dst_output_mask}"
            if self.out_mux == OMUX_MAC:
                mac.append(out_destination)
            else:
                assert self.out_mux == OMUX_ILU
                ilu.append(out_destination)

        if mac_temp_destination:
            mac.append(mac_temp_destination)
        if ilu_temp_destination:
            ilu.append(ilu_temp_destination)

        # ARL implicitly writes to A0 and implicitly uses an "x" write mask.
        if self.mac == self.mac == MAC.MAC_ARL:
            assert not mac
            mac = [f"{DESTINATION_REGISTER_TO_NAME_MAP_SHORT[OutputRegisters.REG_A0]}"]

        return mac, ilu

    def _disassemble_operands(self) -> Tuple[str, str]:
        """Returns a pair of operands for (mac, ilu)."""
        mac = ""
        ilu = ""
        if self.mac:
            mac = MAC_NAMES[self.mac]
        if self.ilu:
            ilu = ILU_NAMES[self.ilu]
        return mac, ilu

    def _filter_mac_inputs(self, inputs) -> List[str]:
        if self.mac == MAC.MAC_MOV or self.mac == MAC.MAC_ARL:
            mac_inputs = [inputs[0]]
        elif self.mac in {
            MAC.MAC_MUL,
            MAC.MAC_DP3,
            MAC.MAC_DP4,
            MAC.MAC_DPH,
            MAC.MAC_DST,
            MAC.MAC_MIN,
            MAC.MAC_MAX,
            MAC.MAC_SGE,
            MAC.MAC_SLT,
        }:
            mac_inputs = [inputs[0], inputs[1]]
        elif self.mac == MAC.MAC_ADD:
            mac_inputs = [inputs[0], inputs[2]]
        elif self.mac == MAC.MAC_MAD:
            mac_inputs = inputs
        else:
            raise Exception(f"Unsupported MAC operand {self.mac}")
        return mac_inputs

    def disassemble_to_dict(self) -> dict:
        mac, ilu = self._disassemble_operands()
        mac_outputs, ilu_outputs = self._disassemble_outputs()
        inputs = self._dissasemble_inputs()

        def _build(mnemonic, outputs, inputs):
            return {
                "mnemonic": mnemonic,
                "outputs": outputs,
                "inputs": inputs,
            }

        ret = {}
        if mac:
            ret["mac"] = _build(mac, mac_outputs, self._filter_mac_inputs(inputs))

        if ilu:
            ret["ilu"] = _build(ilu, ilu_outputs, [inputs[2]])

        return ret

    def disassemble(self) -> str:
        """Disassembles this instruction into assembly language."""
        info = self.disassemble_to_dict()

        ret = []
        mac = info.get("mac")
        if mac:
            mnemonic = mac["mnemonic"]
            outputs = mac["outputs"]
            inputs = mac["inputs"]

            for output in outputs:
                mac_str = f"{mnemonic} {output}, " + ", ".join(inputs)
                ret.append(mac_str)

        ilu = info.get("ilu")
        if ilu:
            mnemonic = ilu["mnemonic"]
            outputs = ilu["outputs"]
            inputs = ilu["inputs"]

            for output in outputs:
                ilu_str = f"{mnemonic} {output}, " + ", ".join(inputs)
                ret.append(ilu_str)

        return " + ".join(ret)

    def explain(self) -> str:
        """Returns a verbose description of this instruction's fields."""

        values = []

        for f in _B._fields_:
            val = getattr(self._b, f[0])
            name = f[0]
            values.append(f"{name}: 0x{val:x} ({val:0{f[2]}b})")
        for f in _C._fields_:
            val = getattr(self._c, f[0])
            name = f[0]
            values.append(f"{name}: 0x{val:x} ({val:0{f[2]}b})")
        for f in _D._fields_:
            val = getattr(self._d, f[0])
            name = f[0]
            values.append(f"{name}: 0x{val:x} ({val:0{f[2]}b})")

        pretty_raw_values = ", ".join([f"0x{val:08X}" for val in self.encode()])
        return f"{pretty_raw_values}:\n\t" + "\n\t".join(values)


def vsh_diff_instructions(
    expected: List[int], actual: List[int], ignore_final_flag=False
) -> str:
    """Provides a verbose explanation of the difference of two encoded instructions.

    :return "" if the instructions match, else a string explaining the delta.
    """

    differences = []
    if expected[0] != actual[0]:
        assert expected[0] == 0
        differences.append(f"Invalid instruction, [0](0x{actual[0]:08x} must == 0")

    e_b = _B.from_buffer_copy(expected[1].to_bytes(4, byteorder=sys.byteorder))
    a_b = _B.from_buffer_copy(actual[1].to_bytes(4, byteorder=sys.byteorder))

    for f in _B._fields_:
        e_val = getattr(e_b, f[0])
        a_val = getattr(a_b, f[0])

        if e_val != a_val:
            name = f[0]

            differences.append(
                f"{name} 0x{e_val:x} ({e_val:0{f[2]}b}) != actual 0x{a_val:x} ({a_val:0{f[2]}b})"
            )

    e_c = _C.from_buffer_copy(expected[2].to_bytes(4, byteorder=sys.byteorder))
    a_c = _C.from_buffer_copy(actual[2].to_bytes(4, byteorder=sys.byteorder))
    for f in _C._fields_:
        e_val = getattr(e_c, f[0])
        a_val = getattr(a_c, f[0])

        if e_val != a_val:
            name = f[0]

            differences.append(
                f"{name} 0x{e_val:x} ({e_val:0{f[2]}b}) != actual 0x{a_val:x} ({a_val:0{f[2]}b})"
            )

    e_d = _D.from_buffer_copy(expected[3].to_bytes(4, byteorder=sys.byteorder))
    a_d = _D.from_buffer_copy(actual[3].to_bytes(4, byteorder=sys.byteorder))
    for f in _D._fields_:
        if ignore_final_flag and f[0] == "FINAL":
            continue

        e_val = getattr(e_d, f[0])
        a_val = getattr(a_d, f[0])

        if e_val != a_val:
            name = f[0]

            differences.append(
                f"{name} 0x{e_val:x} ({e_val:0{f[2]}b}) != actual 0x{a_val:x} ({a_val:0{f[2]}b})"
            )

    if not differences:
        return ""

    return (
        (
            "Instructions differ.\n"
            f"\t0x{expected[0]:08x} 0x{expected[1]:08x} 0x{expected[2]:08x} 0x{expected[3]:08x}\n"
            f"\t0x{actual[0]:08x} 0x{actual[1]:08x} 0x{actual[2]:08x} 0x{actual[3]:08x}\n"
            "\n\t"
        )
        + "\n\t".join(differences)
        + "\n"
    )


def explain(values: List[int]) -> str:
    """Returns a textual description of the given machine code quadruplet."""
    vsh = VshInstruction(True)
    vsh.set_values(values)
    return vsh.explain()
