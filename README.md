Trivial assembler for the nv2a vertex shader.

The Cg -> vp20 path performs various optimizations that sometimes make it hard
to force unusual test conditions. This assembler performs no optimizations, and
simply translates operands into machine code.


## Instructions

* `ADD dst, src1, src2`
    * Sum `dst = src1 + src2`
* `ARL a0, src`
    * Load address register - `a0 = src`
* `DP3 dst, src1, src2`
    * 3-component (xyz) dot product - `dst = src1 dotproduct_xyz src2`
* `DP4 dst, src1, src2`
    * 4-component (xyzw) dot product - `dst = src1 dotproduct_xyzw src2`
* `DPH dst, src1, src2`
    * Homogenous dot product - `dst = src1.x * src2.x + src1.y * src2.y + src1.z * src2.z + src2.w`
* `DST dst, src1, src2`
    * Compute distance vector. `src1.yz` should be `distance squared`,  `src2.yw` should be `1.0 / distance`

    ```
    dst.x = 1.0
    dst.y = src1.y * src2.y
    dst.z = src1.z
    dst.w = src2.w
    ```

* `EXPP dst, src`
  * Partial precision `2^x` exponentiation.

    ```
    x_floor = floorf(src.x)
    dst.x = pow(2.0f, x_floor)
    dst.y = src.x - x_floor
    dst.z = pow(2.0f, src.x)
    dst.w = 1.0f
    ```
* `LIT dst, src`
  * Calculate lighting coefficients
    The src vector should be initialized with:

    `src.x = normal dotproduct direction_to_light`

     `src.y = normal dotproduct light_half_vector`

     `src.w = power`

    ```
    kMax = 127.9961f

    dst.x = 1.0f
    dst.y = 0.0f
    dst.z = 0.0f
    dst.w = 1.0f

    power = clamp(src.w, -kMax, kMax)

    if (src.x > 0.0f) {

      dst.x = src.x

      if (src.y > 0.0f) {
        dst.z = pow(src.y, power)
      }

    }
    ```
* `LOGP dst, src`
  * Partial precision base 2 logarithm
  ```
  dst.x = exponent
  dst.y = mantissa
  dst.z = log2(abs(src.x))
  ```
* `MAD dst, src1, src2, src3`
  * Multiplies two sources, then adds a third. `dst = src1 * src2 + src3`
* `MAX dst, src1, src2`
  * Returns the component-wise maximum between two vectors. `dst.C = max(src1.C, src2.C); for C in {x, y, z, w}`
* `MIN dst, src1, src2`
  * Returns the component-wise minimum between two vectors. `dst.C = min(src1.C, src2.C); for C in {x, y, z, w}`
* `MOV dst, src`
  * Assigns the value of one register to another. `dst = src`
* `MUL dst, src1, src2`
    * Multiply `dst = src1 * src2`
* `RCC dst, src`
  * Compute clamped reciprocal. `dst.xyzw = 1 / src[.x]` clamped to ~(5.42101e-020f, 1.884467e+019)
* `RCP dst, src`
  * Compute reciprocal. `dst.xyzw = 1 / src[.x]`
* `RSQ dst, src`
  * Compute reciprocal of the square root. `dst.xyzw = 1 / sqrt(src[.x])`
* `SGE dst, src1, src2`
  * Per component greater than or equal comparison. `dst.C = 1.0 if src1.C >= src2.C else 0.0; for C in {x, y, z, w}`
* `SLT dst, src1, src2`
  * Per component less than comparison. `dst.C = 1.0 if src1.C < src2.C else 0.0; for C in {x, y, z, w}`
* `SUB dst, src1, src2`
    * Difference `dst = src1 - src2`

## Registers

### Temporary registers
* `r0` - `r11`
* `r12` - read-only view of the `oPos` output register

### Constant/uniform registers
* `c0` - `c191`

Constant registers may also use relative addressing via bracket syntax. E.g.,
`c[a0 + 12]`

### Address register
* `a0`

May only be set via the `ARL` instruction. E.g., `ARL a0, v12`

### Inputs

* `v0`, `iPos`
* `v1`, `iWeight`
* `v2`, `iNormal`
* `v3`, `iDiffuse`
* `v4`, `iSpecular`
* `v5`, `iFog`
* `v6`, `iPts`
* `v7`, `iBackDiffuse`
* `v8`, `iBackSpecular`
* `v9`, `iTex0`
* `v10`, `iTex1`
* `v11`, `iTex2`
* `v12`, `iTex3`
* `v13`
* `v14`
* `v15`

### Outputs

* `oB0`, `oBackDiffuse`
* `oB1`, `oBackSpecular`
* `oD0`, `oDiffuse`
* `oD1`, `oSpecular`
* `oFog`
* `oPos`
* `oPts`
* `oTex0`, `oT0`
* `oTex1`, `oT1`
* `oTex2`, `oT2`
* `oTex3`, `oT3`

### Swizzle/destination masks

* `xyzw`
* `rgba`


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


## Operation macros

Higher level operations are supported via macros that expand to multiple
instructions.

### matmul4x4 - Multiply a 4 element vector by a 4x4 matrix

`%matmul4x4 <dst> <register> <#matrix4_uniform>`

Expands to 4 commands.

```
%matmul4x4 r0 iPos #model_matrix
------------------------------------
dp4 r0.x, iPos, #model_matrix[0]
dp4 r0.y, iPos, #model_matrix[1]
dp4 r0.z, iPos, #model_matrix[2]
dp4 r0.w, iPos, #model_matrix[3]
```
