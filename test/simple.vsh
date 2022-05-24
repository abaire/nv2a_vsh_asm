MOV R1.xyzw, v0
// [0x00000000, 0x0020001B, 0x0836106C, 0x2F100FF8]

RCP oFog.xyzw, v0.w
// [0x00000000, 0x0400001B, 0x083613FC, 0x2070F82C]

ADD oPos.xyzw, R2, c[1]
// [0x00000000, 0x0060201B, 0x2436106C, 0x3070F800]

MOV oPts.xyzw, v1.x
// [0x00000000, 0x00200200, 0x0836106C, 0x2070F830]

MOV oB0.xyzw, v7
// [0x00000000, 0x00200E1B, 0x0836106C, 0x2070F838]

MOV oB1.xyzw, v8
// [0x00000000, 0x0020101B, 0x0836106C, 0x2070F840]

MOV oT0.xyzw, v9
// [0x00000000, 0x0020121B, 0x0836106C, 0x2070F848]

MOV oT1.xyzw, v10
// [0x00000000, 0x0020141B, 0x0836106C, 0x2070F850]

MOV oT2.xyzw, v11
// [0x00000000, 0x0020161B, 0x0836106C, 0x2070F858]

MOV oT3.xyzw, v12
// [0x00000000, 0x0020181B, 0x0836106C, 0x2070F860]

/*
 The 0th bit of the last test case must be set to 1 to indicate that it is the end
 of the program. (test_simple in test_vsh_assembler uses inline_final_flag)
*/

ADD R6.xyz, c17, -R10
// [0x00000000, 0x0062201B, 0x0C36146E, 0x9E600FF9]
