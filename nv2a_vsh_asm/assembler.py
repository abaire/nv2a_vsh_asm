"""nv2a vertex shader language assembler"""
from typing import List

import antlr4
from build.grammar.VshLexer import VshLexer
from build.grammar.VshParser import VshParser

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
        return self._output

    def get_c_output(self):
        lines = []

        for (a, b, c, d), source in zip(self._output, self._pretty_sources):
            lines.append(f"/* {source} */")
            lines.append(f"0x{a:08x}, 0x{b:08x}, 0x{c:08x}, 0x{d:08x},")

        return "\n".join(lines)
