"""Common constants for the vertex shader encoder."""

import enum

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
    ILU_NOP = 0
    ILU_MOV = 1
    ILU_RCP = 2
    ILU_RCC = 3
    ILU_RSQ = 4
    ILU_EXP = 5
    ILU_LOG = 6
    ILU_LIT = 7


class MAC(enum.IntEnum):
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
