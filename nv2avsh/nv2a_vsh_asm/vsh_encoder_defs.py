"""Common constants for the vertex shader encoder."""

import enum
from typing import Optional

SWIZZLE_X = 0
SWIZZLE_Y = 1
SWIZZLE_Z = 2
SWIZZLE_W = 3
SWIZZLE_ZERO = 4
SWIZZLE_ONE = 5
SWIZZLE_NIL = 7

PARAM_UNKNOWN = 0
PARAM_R = 1
PARAM_V = 2
PARAM_C = 3

OUTPUT_C = 0
OUTPUT_O = 1

OMUX_MAC = 0
OMUX_ILU = 1


class ILU(enum.IntEnum):
    """The operations that execute on the ILU."""

    ILU_NOP = 0
    ILU_MOV = 1
    ILU_RCP = 2
    ILU_RCC = 3
    ILU_RSQ = 4
    ILU_EXP = 5
    ILU_LOG = 6
    ILU_LIT = 7


ILU_NAMES = {
    ILU.ILU_NOP: "NOP",
    ILU.ILU_MOV: "MOV",
    ILU.ILU_RCP: "RCP",
    ILU.ILU_RCC: "RCC",
    ILU.ILU_RSQ: "RSQ",
    ILU.ILU_EXP: "EXP",
    ILU.ILU_LOG: "LOG",
    ILU.ILU_LIT: "LIT",
}


class MAC(enum.IntEnum):
    """The operations that execute on the MAC."""

    MAC_NOP = 0
    MAC_MOV = 1
    MAC_MUL = 2
    MAC_ADD = 3
    MAC_MAD = 4
    MAC_DP3 = 5
    MAC_DPH = 6
    MAC_DP4 = 7
    MAC_DST = 8
    MAC_MIN = 9
    MAC_MAX = 10
    MAC_SLT = 11
    MAC_SGE = 12
    MAC_ARL = 13


MAC_NAMES = {
    MAC.MAC_NOP: "NOP",
    MAC.MAC_MOV: "MOV",
    MAC.MAC_MUL: "MUL",
    MAC.MAC_ADD: "ADD",
    MAC.MAC_MAD: "MAD",
    MAC.MAC_DP3: "DP3",
    MAC.MAC_DPH: "DPH",
    MAC.MAC_DP4: "DP4",
    MAC.MAC_DST: "DST",
    MAC.MAC_MIN: "MIN",
    MAC.MAC_MAX: "MAX",
    MAC.MAC_SLT: "SLT",
    MAC.MAC_SGE: "SGE",
    MAC.MAC_ARL: "ARL",
}


def make_swizzle(
    x_slot: int,
    y_slot: Optional[int] = None,
    z_slot: Optional[int] = None,
    w_slot: Optional[int] = None,
) -> int:
    """Creates a swizzle mask from the given components."""
    if y_slot is None:
        y_slot = z_slot = w_slot = x_slot
    elif z_slot is None:
        z_slot = w_slot = y_slot
    elif w_slot is None:
        w_slot = z_slot

    return ((x_slot) << 0) | ((y_slot) << 3) | ((z_slot) << 6) | ((w_slot) << 9)


SWIZZLE_XYZW = make_swizzle(SWIZZLE_X, SWIZZLE_Y, SWIZZLE_Z, SWIZZLE_W)
SWIZZLE_XXXX = make_swizzle(SWIZZLE_X, SWIZZLE_X, SWIZZLE_X, SWIZZLE_X)
SWIZZLE_YYYY = make_swizzle(SWIZZLE_Y, SWIZZLE_Y, SWIZZLE_Y, SWIZZLE_Y)
SWIZZLE_ZZZZ = make_swizzle(SWIZZLE_Z, SWIZZLE_Z, SWIZZLE_Z, SWIZZLE_Z)
SWIZZLE_WWWW = make_swizzle(SWIZZLE_W, SWIZZLE_W, SWIZZLE_W, SWIZZLE_W)

WRITEMASK_X = 0x1
WRITEMASK_Y = 0x2
WRITEMASK_XY = 0x3
WRITEMASK_Z = 0x4
WRITEMASK_XZ = 0x5
WRITEMASK_YZ = 0x6
WRITEMASK_XYZ = 0x7
WRITEMASK_W = 0x8
WRITEMASK_XW = 0x9
WRITEMASK_YW = 0xA
WRITEMASK_XYW = 0xB
WRITEMASK_ZW = 0xC
WRITEMASK_XZW = 0xD
WRITEMASK_YZW = 0xE
WRITEMASK_XYZW = 0xF

MASK_W = 1
MASK_Z = 2
MASK_ZW = 3
MASK_Y = 4
MASK_YW = 5
MASK_YZ = 6
MASK_YZW = 7
MASK_X = 8
MASK_XW = 9
MASK_XZ = 10
MASK_XZW = 11
MASK_XY = 12
MASK_XYW = 13
MASK_XYZ = 14
MASK_XYZW = 15

VSH_MASK = {
    WRITEMASK_X: MASK_X,
    WRITEMASK_Y: MASK_Y,
    WRITEMASK_XY: MASK_XY,
    WRITEMASK_Z: MASK_Z,
    WRITEMASK_XZ: MASK_XZ,
    WRITEMASK_YZ: MASK_YZ,
    WRITEMASK_XYZ: MASK_XYZ,
    WRITEMASK_W: MASK_W,
    WRITEMASK_XW: MASK_XW,
    WRITEMASK_YW: MASK_YW,
    WRITEMASK_XYW: MASK_XYW,
    WRITEMASK_ZW: MASK_ZW,
    WRITEMASK_XZW: MASK_XZW,
    WRITEMASK_YZW: MASK_YZW,
    WRITEMASK_XYZW: MASK_XYZW,
}

WRITEMASK_NAME = {
    WRITEMASK_X: ".x",
    WRITEMASK_Y: ".y",
    WRITEMASK_XY: ".xy",
    WRITEMASK_Z: ".z",
    WRITEMASK_XZ: ".xz",
    WRITEMASK_YZ: ".yz",
    WRITEMASK_XYZ: ".xyz",
    WRITEMASK_W: ".w",
    WRITEMASK_XW: ".xw",
    WRITEMASK_YW: ".yw",
    WRITEMASK_XYW: ".xyw",
    WRITEMASK_ZW: ".zw",
    WRITEMASK_XZW: ".xzw",
    WRITEMASK_YZW: ".yzw",
    WRITEMASK_XYZW: "",
}


class InputRegisters(enum.IntEnum):
    """Defines the valid input registers for nv2a hardware."""

    REG_POS = 0
    V0 = 0
    REG_WEIGHT = 1
    V1 = 1
    REG_NORMAL = 2
    V2 = 2
    REG_DIFFUSE = 3
    V3 = 3
    REG_SPECULAR = 4
    V4 = 4
    REG_FOG_COORD = 5
    V5 = 5
    REG_POINT_SIZE = 6
    V6 = 6
    REG_BACK_DIFFUSE = 7
    V7 = 7
    REG_BACK_SPECULAR = 8
    V8 = 8
    REG_TEX0 = 9
    V9 = 9
    REG_TEX1 = 10
    V10 = 10
    REG_TEX2 = 11
    V11 = 11
    REG_TEX3 = 12
    V12 = 12
    V13 = 13
    V14 = 14
    V15 = 15


class OutputRegisters(enum.IntEnum):
    """Defines the valid output registers for nv2a hardware."""

    REG_POS = 0
    # REG_WEIGHT = 1
    # REG_NORMAL = 2
    REG_DIFFUSE = 3
    REG_SPECULAR = 4
    REG_FOG_COORD = 5
    REG_POINT_SIZE = 6
    REG_BACK_DIFFUSE = 7
    REG_BACK_SPECULAR = 8
    REG_TEX0 = 9
    REG_TEX1 = 10
    REG_TEX2 = 11
    REG_TEX3 = 12
    # REG_13 = 13
    # REG_14 = 14

    REG_A0 = 9999


DESTINATION_REGISTER_TO_NAME_MAP = {
    OutputRegisters.REG_POS: "oPos",
    OutputRegisters.REG_DIFFUSE: "oDiffuse",
    OutputRegisters.REG_SPECULAR: "oSpecular",
    OutputRegisters.REG_FOG_COORD: "oFog",
    OutputRegisters.REG_POINT_SIZE: "oPts",
    OutputRegisters.REG_BACK_DIFFUSE: "oBackDiffuse",
    OutputRegisters.REG_BACK_SPECULAR: "oBackSpecular",
    OutputRegisters.REG_TEX0: "oTex0",
    OutputRegisters.REG_TEX1: "oTex1",
    OutputRegisters.REG_TEX2: "oTex2",
    OutputRegisters.REG_TEX3: "oTex3",
    OutputRegisters.REG_A0: "A0",
}

DESTINATION_REGISTER_TO_NAME_MAP_SHORT = {
    OutputRegisters.REG_POS: "oPos",
    OutputRegisters.REG_DIFFUSE: "oD0",
    OutputRegisters.REG_SPECULAR: "oD1",
    OutputRegisters.REG_FOG_COORD: "oFog",
    OutputRegisters.REG_POINT_SIZE: "oPts",
    OutputRegisters.REG_BACK_DIFFUSE: "oB0",
    OutputRegisters.REG_BACK_SPECULAR: "oB1",
    OutputRegisters.REG_TEX0: "oT0",
    OutputRegisters.REG_TEX1: "oT1",
    OutputRegisters.REG_TEX2: "oT2",
    OutputRegisters.REG_TEX3: "oT3",
    OutputRegisters.REG_A0: "A0",
}
