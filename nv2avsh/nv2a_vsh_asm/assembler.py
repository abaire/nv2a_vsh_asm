"""nv2a vertex shader language assembler"""
from typing import List

import antlr4
from nv2avsh.grammar.vsh.VshLexer import VshLexer
from nv2avsh.grammar.vsh.VshParser import VshParser

from . import vsh_encoder
from . import encoding_visitor


class Assembler:
    """Assembles nv2a vertex shader assembly code."""

    def __init__(self, source: str):
        self._source = source
        self._output = []
        self._pretty_sources = []

    def assemble(self, **kwargs) -> bool:
        """Assembles the source code and populates the output byte array"""
        input_stream = antlr4.InputStream(self._source)
        lexer = VshLexer(input_stream)
        token_stream = antlr4.CommonTokenStream(lexer)
        parser = VshParser(token_stream)

        visitor = encoding_visitor.EncodingVisitor()
        program = visitor.visit(parser.program())
        if not program:
            self._output = []
            self._pretty_sources = []
            return True

        instructions, sources = zip(*program)
        self._output = vsh_encoder.encode(instructions, **kwargs)
        self._pretty_sources = sources
        return True

    @property
    def output(self) -> List[List[int]]:
        """Retrieves the assembled list of machine code quadruplets."""
        return self._output

    def get_c_output(self) -> str:
        """Retrieves the assembled machine code as a C-like string."""
        lines = []

        for (int_0, int_1, int_2, int_3), source in zip(
            self._output, self._pretty_sources
        ):
            lines.append(f"/* {source} */")
            lines.append(f"0x{int_0:08x}, 0x{int_1:08x}, 0x{int_2:08x}, 0x{int_3:08x},")

        if len(self._output) == len(self._pretty_sources) + 1:
            lines.append(f"/* <NOP FINAL MARKER> */")
            int_0, int_1, int_2, int_3 = self._output[-1]
            lines.append(f"0x{int_0:08x}, 0x{int_1:08x}, 0x{int_2:08x}, 0x{int_3:08x},")

        return "\n".join(lines)
