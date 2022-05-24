"""Provides functionality for manipulating nv2a vertex shader machine code."""
import ctypes
import struct
from typing import List

from .vsh_encoder_defs import *


class _B(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("FLD_A_SWZ_W", ctypes.c_uint32, 2),
        ("FLD_A_SWZ_Z", ctypes.c_uint32, 2),
        ("FLD_A_SWZ_Y", ctypes.c_uint32, 2),
        ("FLD_A_SWZ_X", ctypes.c_uint32, 2),
        ("FLD_A_NEG", ctypes.c_uint32, 1),
        ("FLD_V", ctypes.c_uint32, 4),
        ("FLD_CONST", ctypes.c_uint32, 8),
        ("FLD_MAC", ctypes.c_uint32, 4),
        ("FLD_ILU", ctypes.c_uint32, 3),
    ]


class _C(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("FLD_C_R_HIGH", ctypes.c_uint32, 2),
        ("FLD_C_SWZ_W", ctypes.c_uint32, 2),
        ("FLD_C_SWZ_Z", ctypes.c_uint32, 2),
        ("FLD_C_SWZ_Y", ctypes.c_uint32, 2),
        ("FLD_C_SWZ_X", ctypes.c_uint32, 2),
        ("FLD_C_NEG", ctypes.c_uint32, 1),
        ("FLD_B_MUX", ctypes.c_uint32, 2),
        ("FLD_B_R", ctypes.c_uint32, 4),
        ("FLD_B_SWZ_W", ctypes.c_uint32, 2),
        ("FLD_B_SWZ_Z", ctypes.c_uint32, 2),
        ("FLD_B_SWZ_Y", ctypes.c_uint32, 2),
        ("FLD_B_SWZ_X", ctypes.c_uint32, 2),
        ("FLD_B_NEG", ctypes.c_uint32, 1),
        ("FLD_A_MUX", ctypes.c_uint32, 2),
        ("FLD_A_R", ctypes.c_uint32, 4),
    ]


class _D(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("FLD_FINAL", ctypes.c_uint32, 1),
        ("FLD_A0X", ctypes.c_uint32, 1),
        ("FLD_OUT_MUX", ctypes.c_uint32, 1),
        ("FLD_OUT_ADDRESS", ctypes.c_uint32, 8),
        ("FLD_OUT_ORB", ctypes.c_uint32, 1),
        ("FLD_OUT_O_MASK", ctypes.c_uint32, 4),
        ("FLD_OUT_ILU_MASK", ctypes.c_uint32, 4),
        ("FLD_OUT_R", ctypes.c_uint32, 4),
        ("FLD_OUT_MAC_MASK", ctypes.c_uint32, 4),
        ("FLD_C_MUX", ctypes.c_uint32, 2),
        ("FLD_C_R_LOW", ctypes.c_uint32, 2),
    ]


def get_swizzle(swz: int, idx: int) -> int:
    """Extracts the swizzle component at `idx` from `swz`."""
    return ((swz) >> ((idx) * 3)) & 0x7


class VshInstruction:
    """Models nv2a vertex shader machine code."""

    def __init__(self):
        self._b = _B()
        self._c = _C()
        self._d = _D()

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

        self.out_r = 7
        self.out_address = 0xFF
        self.out_mux = OMUX_MAC
        self.out_orb = OUTPUT_O

    def set_empty_final(self):
        zero = bytes(b"\0" * 4)
        self._b = _B.from_buffer_copy(zero)
        self._c = _C.from_buffer_copy(zero)
        self._d = _D.from_buffer_copy(zero)
        self.final = True

    @property
    def a_swizzle_w(self) -> int:
        return self._b.FLD_A_SWZ_W

    @a_swizzle_w.setter
    def a_swizzle_w(self, val: int):
        self._b.FLD_A_SWZ_W = val

    @property
    def a_swizzle_z(self) -> int:
        return self._b.FLD_A_SWZ_Z

    @a_swizzle_z.setter
    def a_swizzle_z(self, val: int):
        self._b.FLD_A_SWZ_Z = val

    @property
    def a_swizzle_y(self) -> int:
        return self._b.FLD_A_SWZ_Y

    @a_swizzle_y.setter
    def a_swizzle_y(self, val: int):
        self._b.FLD_A_SWZ_Y = val

    @property
    def a_swizzle_x(self) -> int:
        return self._b.FLD_A_SWZ_X

    @a_swizzle_x.setter
    def a_swizzle_x(self, val: int):
        self._b.FLD_A_SWZ_X = val

    @property
    def a_negate(self) -> bool:
        return bool(self._b.FLD_A_NEG)

    @a_negate.setter
    def a_negate(self, val: bool):
        if val:
            self._b.FLD_A_NEG = 1
        else:
            self._b.FLD_A_NEG = 0

    # TODO: Rename to input_reg
    @property
    def v(self) -> int:
        return self._b.FLD_V

    @v.setter
    def v(self, val: int):
        self._b.FLD_V = val

    # TODO: Rename to const_reg
    @property
    def const(self) -> int:
        return self._b.FLD_CONST

    @const.setter
    def const(self, val: int):
        self._b.FLD_CONST = val

    @property
    def mac(self) -> int:
        return self._b.FLD_MAC

    @mac.setter
    def mac(self, val: int):
        self._b.FLD_MAC = val

    @property
    def ilu(self) -> int:
        return self._b.FLD_ILU

    @ilu.setter
    def ilu(self, val: int):
        self._b.FLD_ILU = val

    @property
    def c_r(self) -> int:
        return (self.c_r_high & 0x03) << 2 + (self.c_r_low & 0x03)

    @c_r.setter
    def c_r(self, val: int):
        self.c_r_low = val & 0x03
        self.c_r_high = (val >> 2) & 0x03

    @property
    def c_r_high(self) -> int:
        return self._c.FLD_C_R_HIGH

    @c_r_high.setter
    def c_r_high(self, val: int):
        self._c.FLD_C_R_HIGH = val

    @property
    def c_swizzle_w(self) -> int:
        return self._c.FLD_C_SWZ_W

    @c_swizzle_w.setter
    def c_swizzle_w(self, val: int):
        self._c.FLD_C_SWZ_W = val

    @property
    def c_swizzle_z(self) -> int:
        return self._c.FLD_C_SWZ_Z

    @c_swizzle_z.setter
    def c_swizzle_z(self, val: int):
        self._c.FLD_C_SWZ_Z = val

    @property
    def c_swizzle_y(self) -> int:
        return self._c.FLD_C_SWZ_Y

    @c_swizzle_y.setter
    def c_swizzle_y(self, val: int):
        self._c.FLD_C_SWZ_Y = val

    @property
    def c_swizzle_x(self) -> int:
        return self._c.FLD_C_SWZ_X

    @c_swizzle_x.setter
    def c_swizzle_x(self, val: int):
        self._c.FLD_C_SWZ_X = val

    @property
    def c_negate(self) -> bool:
        return bool(self._c.FLD_C_NEG)

    @c_negate.setter
    def c_negate(self, val: bool):
        if val:
            self._c.FLD_C_NEG = 1
        else:
            self._c.FLD_C_NEG = 0

    @property
    def b_mux(self) -> int:
        return self._c.FLD_B_MUX

    @b_mux.setter
    def b_mux(self, val: int):
        self._c.FLD_B_MUX = val

    @property
    def b_r(self) -> int:
        return self._c.FLD_B_R

    @b_r.setter
    def b_r(self, val: int):
        self._c.FLD_B_R = val

    @property
    def b_swizzle_w(self) -> int:
        return self._c.FLD_B_SWZ_W

    @b_swizzle_w.setter
    def b_swizzle_w(self, val: int):
        self._c.FLD_B_SWZ_W = val

    @property
    def b_swizzle_z(self) -> int:
        return self._c.FLD_B_SWZ_Z

    @b_swizzle_z.setter
    def b_swizzle_z(self, val: int):
        self._c.FLD_B_SWZ_Z = val

    @property
    def b_swizzle_y(self) -> int:
        return self._c.FLD_B_SWZ_Y

    @b_swizzle_y.setter
    def b_swizzle_y(self, val: int):
        self._c.FLD_B_SWZ_Y = val

    @property
    def b_swizzle_x(self) -> int:
        return self._c.FLD_B_SWZ_X

    @b_swizzle_x.setter
    def b_swizzle_x(self, val: int):
        self._c.FLD_B_SWZ_X = val

    @property
    def b_negate(self) -> bool:
        return bool(self._c.FLD_B_NEG)

    @b_negate.setter
    def b_negate(self, val: bool):
        if val:
            self._c.FLD_B_NEG = 1
        else:
            self._c.FLD_B_NEG = 0

    @property
    def a_mux(self) -> int:
        return self._c.FLD_A_MUX

    @a_mux.setter
    def a_mux(self, val: int):
        self._c.FLD_A_MUX = val

    # TODO: Rename *_r to *_reg
    @property
    def a_r(self) -> int:
        return self._c.FLD_A_R

    @a_r.setter
    def a_r(self, val: int):
        self._c.FLD_A_R = val

    @property
    def final(self) -> bool:
        return bool(self._d.FLD_FINAL)

    @final.setter
    def final(self, val: bool):
        if val:
            self._d.FLD_FINAL = 1
        else:
            self._d.FLD_FINAL = 0

    @property
    def a0x(self) -> bool:
        return bool(self._d.FLD_A0X)

    @a0x.setter
    def a0x(self, val: bool):
        if val:
            self._d.FLD_A0X = 1
        else:
            self._d.FLD_A0X = 0

    @property
    def out_mux(self) -> bool:
        return bool(self._d.FLD_OUT_MUX)

    @out_mux.setter
    def out_mux(self, val: bool):
        if val:
            self._d.FLD_OUT_MUX = 1
        else:
            self._d.FLD_OUT_MUX = 0

    @property
    def out_address(self) -> int:
        return self._c.FLD_OUT_ADDRESS

    @out_address.setter
    def out_address(self, val: int):
        self._c.FLD_OUT_ADDRESS = val

    @property
    def out_orb(self) -> bool:
        return bool(self._d.FLD_OUT_ORB)

    @out_orb.setter
    def out_orb(self, val: bool):
        if val:
            self._d.FLD_OUT_ORB = 1
        else:
            self._d.FLD_OUT_ORB = 0

    @property
    def out_o_mask(self) -> int:
        return self._c.FLD_OUT_O_MASK

    @out_o_mask.setter
    def out_o_mask(self, val: int):
        self._c.FLD_OUT_O_MASK = val

    @property
    def out_ilu_mask(self) -> int:
        return self._c.FLD_OUT_ILU_MASK

    @out_ilu_mask.setter
    def out_ilu_mask(self, val: int):
        self._c.FLD_OUT_ILU_MASK = val

    @property
    def out_r(self) -> int:
        return self._c.FLD_OUT_R

    @out_r.setter
    def out_r(self, val: int):
        self._c.FLD_OUT_R = val

    @property
    def out_mac_mask(self) -> int:
        return self._c.FLD_OUT_MAC_MASK

    @out_mac_mask.setter
    def out_mac_mask(self, val: int):
        self._c.FLD_OUT_MAC_MASK = val

    @property
    def c_mux(self) -> int:
        return self._c.FLD_C_MUX

    @c_mux.setter
    def c_mux(self, val: int):
        self._c.FLD_C_MUX = val

    @property
    def c_r_low(self) -> int:
        return self._c.FLD_C_R_LOW

    @c_r_low.setter
    def c_r_low(self, val: int):
        self._c.FLD_C_R_LOW = val

    def encode(self) -> List[int]:
        a = 0
        b = struct.unpack("<L", self._b)[0]
        c = struct.unpack("<L", self._c)[0]
        d = struct.unpack("<L", self._d)[0]

        return [a, b, c, d]

    def set_mux_field(self, i: int, val: int):
        if i == 0:
            self.a_mux = val
        elif i == 1:
            self.b_mux = val
        elif i == 2:
            self.c_mux = val
        else:
            raise Exception(f"Invalid field index {i}")

    def set_reg_field(self, i: int, val: int):
        if i == 0:
            self.a_r = val
        elif i == 1:
            self.b_r = val
        elif i == 2:
            self.c_r = val
        else:
            raise Exception(f"Invalid field index {i}")

    def set_negate_field(self, i: int, val: bool):
        if i == 0:
            self.a_negate = val
        elif i == 1:
            self.b_negate = val
        elif i == 2:
            self.c_negate = val
        else:
            raise Exception(f"Invalid field index {i}")

    def set_swizzle_field(self, i: int, swizzle: int):
        if i == 0:
            self.a_swizzle_x = get_swizzle(swizzle, 0)
            self.a_swizzle_y = get_swizzle(swizzle, 1)
            self.a_swizzle_z = get_swizzle(swizzle, 2)
            self.a_swizzle_w = get_swizzle(swizzle, 3)
        elif i == 1:
            self.b_swizzle_x = get_swizzle(swizzle, 0)
            self.b_swizzle_y = get_swizzle(swizzle, 1)
            self.b_swizzle_z = get_swizzle(swizzle, 2)
            self.b_swizzle_w = get_swizzle(swizzle, 3)
        elif i == 2:
            self.c_swizzle_x = get_swizzle(swizzle, 0)
            self.c_swizzle_y = get_swizzle(swizzle, 1)
            self.c_swizzle_z = get_swizzle(swizzle, 2)
            self.c_swizzle_w = get_swizzle(swizzle, 3)
        else:
            raise Exception(f"Invalid field index {i}")


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

    e_b = _B(expected[1])
    a_b = _B(actual[1])

    for f in _B._fields_:
        e_val = getattr(e_b, f[0])
        a_val = getattr(a_b, f[0])

        if e_val != a_val:
            name = f[0][10:]

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
