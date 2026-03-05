# NV2A Vertex Shader Encoding Guide

This document describes the binary encoding of the NV2A vertex shader instructions. The instruction set is a VLIW (Very Long Instruction Word) architecture where each instruction is 128 bits long.

## Overview

Each instruction is 128 bits wide, composed of four 32-bit little-endian words (Quad A, B, C, D).
- **Quad A (Bits 0-31)**: Reserved/Unused (Always 0).
- **Quad B (Bits 32-63)**: Input A controls, Global Input/Const selections, MAC/ILU OpCodes.
- **Quad C (Bits 64-95)**: Input B and C controls, Mux selectors.
- **Quad D (Bits 96-127)**: Output controls, Writes Masks, Flags.

## Instruction Layout

### Quad A (Bits 0-31)
| Bit Offset | Field Name | Width | Description |
| :--- | :--- | :--- | :--- |
| 0-31 | RESERVED | 32 | Always 0. |

### Quad B (Bits 32-63)
| Bit Offset | Field Name | Width | Description |
| :--- | :--- | :--- | :--- |
| 0-1 | A_SWZ_W | 2 | Swizzle component for Input A (W). |
| 2-3 | A_SWZ_Z | 2 | Swizzle component for Input A (Z). |
| 4-5 | A_SWZ_Y | 2 | Swizzle component for Input A (Y). |
| 6-7 | A_SWZ_X | 2 | Swizzle component for Input A (X). |
| 8 | A_NEG | 1 | Negate Input A. |
| 9-12 | INPUT | 4 | Input Register Index (`v#`) when Mux selects Input. |
| 13-20 | CONST | 8 | Constant Register Index (`c[#]`) when Mux selects Constant. |
| 21-24 | MAC | 4 | MAC Unit Opcode. |
| 25-27 | ILU | 3 | ILU Unit Opcode. |
| 28-31 | UNUSED | 4 | Padding/Unused. |

### Quad C (Bits 64-95)
| Bit Offset | Field Name | Width | Description |
| :--- | :--- | :--- | :--- |
| 0-1 | C_TEMP_REG_HIGH| 2 | High 2 bits of Input C Temporary Register Index. |
| 2-3 | C_SWZ_W | 2 | Swizzle component for Input C (W). |
| 4-5 | C_SWZ_Z | 2 | Swizzle component for Input C (Z). |
| 6-7 | C_SWZ_Y | 2 | Swizzle component for Input C (Y). |
| 8-9 | C_SWZ_X | 2 | Swizzle component for Input C (X). |
| 10 | C_NEG | 1 | Negate Input C. |
| 11-12 | B_MUX | 2 | Source Mux for Input B (0=Temp, 1=Input, 2=Const). |
| 13-16 | B_TEMP_REG | 4 | Input B Temporary Register Index (`R#`). |
| 17-18 | B_SWZ_W | 2 | Swizzle component for Input B (W). |
| 19-20 | B_SWZ_Z | 2 | Swizzle component for Input B (Z). |
| 21-22 | B_SWZ_Y | 2 | Swizzle component for Input B (Y). |
| 23-24 | B_SWZ_X | 2 | Swizzle component for Input B (X). |
| 25 | B_NEG | 1 | Negate Input B. |
| 26-27 | A_MUX | 2 | Source Mux for Input A (0=Temp, 1=Input, 2=Const). |
| 28-31 | A_TEMP_REG | 4 | Input A Temporary Register Index (`R#`). |

### Quad D (Bits 96-127)
| Bit Offset | Field Name | Width | Description |
| :--- | :--- | :--- | :--- |
| 0 | FINAL | 1 | If set, terminates the shader program. |
| 1 | A0X | 1 | If set, adds `A0` to the Constant Register index (`c[A0 + #]`). |
| 2 | OUT_MUX | 1 | Selects source for Output Register Write (0=MAC, 1=ILU). |
| 3-10 | OUT_ADDRESS | 8 | Output Register Index (e.g., `oPos` is 0). |
| 11 | OUT_ORB | 1 | Output Register Bank (0=Constant Memory, 1=Output Registers). Usually 1. |
| 12-15 | OUT_O_MASK | 4 | Write Mask for the final Output Register (`o#`). |
| 16-19 | OUT_ILU_MASK | 4 | Write Mask for the ILU result to Temp/C regs. |
| 20-23 | OUT_TEMP_REG | 4 | Temporary Register Index for ILU/MAC writes. |
| 24-27 | OUT_MAC_MASK | 4 | Write Mask for the MAC result to Temp/C regs. |
| 28-29 | C_MUX | 2 | Source Mux for Input C (0=Temp, 1=Input, 2=Const). |
| 30-31 | C_TEMP_REG_LOW | 2 | Low 2 bits of Input C Temporary Register Index. |

## Field Details

### Source Muxes (A_MUX, B_MUX, C_MUX)
These 2-bit fields select the source type for inputs A, B, and C.
- `0` (**PARAM_R**): Read from Temporary Register (`R#`). Index comes from `X_TEMP_REG` field.
- `1` (**PARAM_V**): Read from Input Register (`v#`). Index comes from `INPUT` field (Quad B).
- `2` (**PARAM_C**): Read from Constant Register (`c[#]`). Index comes from `CONST` field (Quad B).
- `3` (**Reserved/Unknown**): Invalid.

### Opcodes

#### MAC Opcodes (Quad B, 21-24)
| Value | Mnemonic | Description |
| :--- | :--- | :--- |
| 0 | NOP | No Operation |
| 1 | MOV | Move |
| 2 | MUL | Multiply |
| 3 | ADD | Add |
| 4 | MAD | Multiply Add |
| 5 | DP3 | Dot Product 3 |
| 6 | DPH | Dot Product Homogeneous |
| 7 | DP4 | Dot Product 4 |
| 8 | DST | Distance Vector |
| 9 | MIN | Minimum |
| 10 | MAX | Maximum |
| 11 | SLT | Set Less Than |
| 12 | SGE | Set Greater Equal |
| 13 | ARL | Address Register Load (Writes to A0) |

#### ILU Opcodes (Quad B, 25-27)
| Value | Mnemonic | Description |
| :--- | :--- | :--- |
| 0 | NOP | No Operation |
| 1 | MOV | Move |
| 2 | RCP | Reciprocal |
| 3 | RCC | Reciprocal Clamped |
| 4 | RSQ | Reciprocal Square Root |
| 5 | EXP | Exponential |
| 6 | LOG | Logarithm |
| 7 | LIT | Lighting |

### Output Handling

The shader can write to:
1.  **Output Registers (`o#`)**: Using `OUT_ADDRESS` and `OUT_O_MASK`.
    - `OUT_MUX` determines *which* unit (MAC or ILU) provides the value for this write.
    - 0 = MAC Result.
    - 1 = ILU Result.
2.  **Temporary Registers (`R#`)**: Using `OUT_TEMP_REG`.
    - Both MAC and ILU can write to the *same* temp register index in the same cycle, but usually masked differently.
    - `OUT_MAC_MASK`: Mask for MAC result writing to `R[OUT_TEMP_REG]`.
    - `OUT_ILU_MASK`: Mask for ILU result writing to `R[OUT_TEMP_REG]`.
    - **Note**: ILU often forcibly writes to `R1` or specific registers in paired mode, but the encoding allows specifying `OUT_TEMP_REG`.

### Swizzles
2-bit value per component.
- `0`: X
- `1`: Y
- `2`: Z
- `3`: W

### Write Masks
4-bit values (Bit 0=X, 1=Y, 2=Z, 3=W). If a bit is set, that component is written.

### Special Registers
- **R12**: Used as a read-alias for `oPos`.
- **A0**: Address register, written by `ARL`. Used for indirect constant addressing `c[A0 + #]`.

## Interpreting Assembler Output

When referencing `tests/test_disassembler.py`:

**Example:** `MOV oT2.xyzw, v11`
- Hex: `[0x00000000, 0x0020161B, 0x0836106C, 0x2070F858]`

**Analysis:**
- **Quad A**: `00000000`
- **Quad B**: `0020161B`
    - `A_SWZ` (0-7): `1B` (`00011011` -> W=3, Z=2, Y=1, X=0) -> No Swizzle (`.xyzw`).
    - `INPUT` (9-12): `0x002016...` -> Extract bits... `v11`.
    - `MAC`: `MOV`.
- **Quad D**: `2070F858`
    - `OUT_ADDRESS`: `0x58` (88)? No. `OutputRegisters` mapping needed. `oT2` is `REG_TEX2`.
    - `OUT_MUX`: `0` (MAC).
    - `OUT_O_MASK`: `F` (xyzw).
