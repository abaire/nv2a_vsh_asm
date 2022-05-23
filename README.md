Trivial assembler for the nv2a vertex shader.

The Cg -> vp20 path performs various optimizations that sometimes make it hard
to force unusual test conditions. This assembler performs no optimizations, and
simply translates operands into machine code.
