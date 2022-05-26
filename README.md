Trivial assembler for the nv2a vertex shader.

The Cg -> vp20 path performs various optimizations that sometimes make it hard
to force unusual test conditions. This assembler performs no optimizations, and
simply translates operands into machine code.


## Instructions

* ADD
* ARL
* DP3
* DP4
* DPH
* DST
* EXPP
* LIT
* LOGP
* MAD
* MAX
* MIN
* MOV
* MUL
* RCC
* RCP
* RSQ
* SGE
* SLT

## Registers

### Temporary registers
* r0 - r11

### Constant/uniform registers
* c0 - c191

Constant registers may also use relative addressing via bracket syntax. E.g.,
`c[A0 + 12]`

### Address register
* a0

May only be set via the `ARL` instruction. E.g., `ARL a0, v12`

### Inputs

* v0, iPos
* v1, iWeight
* v2, iNormal
* v3, iDiffuse
* v4, iSpecular
* v5, iFog
* v6, iPts
* v7, iBackDiffuse
* v8, iBackSpecular
* v9, iTex0
* v10, iTex1
* v11, iTex2
* v12, iTex3
* v13
* v14
* v15

### Outputs

* oB0, oBackDiffuse
* oB1, oBackSpecular
* oD0, oDiffuse
* oD1, oSpecular
* oFog
* oPos
* oPts
* oTex0, oT0
* oTex1, oT1
* oTex2, oT2
* oTex3, oT3

### Swizzle/destination masks

* xyzw
* rgba

## Uniform macros

A simple macro syntax is supported to allow symbolic naming for `c`-register
access. Two types are currently implemented, `vector` and `matrix4`.

A `vector` type
aliases a single `c` register. E.g., to give a symbolic name to c10:
`#uniform_name vector 10`. The macro can then be used in subsequent
instructions; e.g., `mov r0, #uniform_name`.

A `matrix4` type aliases a contiguous set of 4 `c` registers. E.g., to give a
symbolic name to a model matrix passed at 'c96': `#my_model_matrix matrix4 96`.
To access the second row: `mul r0, v0.y, #my_model_matrix[1]`.
