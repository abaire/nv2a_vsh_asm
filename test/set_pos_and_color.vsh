; Does a basic projection of the input position and passes through the
; diffuse color but leaves other registers unset.

#model_matrix matrix4 96
#view_matrix matrix4 100
#projection_matrix matrix4 104

mul r0, iPos.y, #model_matrix[1]
// [0x00000000, 0x004C2055, 0x0836186C, 0x2F000FF8]
mad r0, iPos.x, #model_matrix[0], r0
// [0x00000000, 0x008C0000, 0x0836186C, 0x1F000FF8]
mad r0, iPos.z, #model_matrix[2], r0
// [0x00000000, 0x008C40AA, 0x0836186C, 0x1F000FF8]
mad r0, iPos.w, #model_matrix[3], r0
// [0x00000000, 0x008C60FF, 0x0836186C, 0x1F000FF8]

mul r1, r0.y, #view_matrix[1]
// [0x00000000, 0x004CA055, 0x0436186C, 0x2F100FF8]
mad r1, r0.x, #view_matrix[0], r1
// [0x00000000, 0x008C8000, 0x0436186C, 0x5F100FF8]
mad r1, r0.z, #view_matrix[2], r1
// [0x00000000, 0x008CC0AA, 0x0436186C, 0x5F100FF8]
mad r0, r0.w, #view_matrix[3], r1
// [0x00000000, 0x008CE0FF, 0x0436186C, 0x5F000FF8]

mul r1, r0.y, #projection_matrix[1]
// [0x00000000, 0x004D2055, 0x0436186C, 0x2F100FF8]
mad r1, r0.x, #projection_matrix[0], r1
// [0x00000000, 0x008D0000, 0x0436186C, 0x5F100FF8]
mad r1, r0.z, #projection_matrix[2], r1
// [0x00000000, 0x008D40AA, 0x0436186C, 0x5F100FF8]
mad r0, r0.w, #projection_matrix[3], r1
// [0x00000000, 0x008D60FF, 0x0436186C, 0x5F000FF8]

; oPos.xyz = r0.xyz / r0.w
rcp r1.x, r0.w
// [0x00000000, 0x0400001B, 0x083613FC, 0x10180FF8]
mul oPos.xyz, r0, r1.x
// [0x00000000, 0x0040001B, 0x0400286C, 0x2070E800]
mov oPos.w, r0
// [0x00000000, 0x0020001B, 0x0436106C, 0x20701800]

mov oD0, iDiffuse
// [0x00000000, 0x0020061B, 0x0836106C, 0x2070F819]
