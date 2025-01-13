add r0.xyz, v0.zzz,c2.wxy
dp3 r2, r0, c[3]
dp4 r2, r0, c[A0+4]
dph r2, r0, c[A0 + 95]
dst r4, r0, r1
expp r5, r0
lit r0, r1
logp r0,r1
mad r0,r1,r2,v3
max r11, r3, r4
min r0, r3, r4
mov r10, v2
mul r4, v0, r1
rcc r1.x, r0.w
rcp oPos, r2
rsq oPos.x, r2
sge r1, r2, v1
slt r1, r2, v1
; sub r2, v2, r2  # TODO: Implement
