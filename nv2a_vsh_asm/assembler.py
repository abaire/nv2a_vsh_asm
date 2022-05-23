"""nv2a vertex shader language assembler"""

import antlr4
from build.grammar.VshLexer import VshLexer
from build.grammar.VshParser import VshParser
from build.grammar.VshVisitor import VshVisitor

class _Visitor(VshVisitor):
    pass

class Assembler:
    """Assembles nv2a vertex shader assembly code."""

    def __init__(self, source: str):
        self._source = source
        self._output = ""

    def assemble(self) -> bool:
        """Assembles the source code and populates the output byte array"""
        input_stream = antlr4.InputStream(self._source)
        lexer = VshLexer(input_stream)
        token_stream = antlr4.CommonTokenStream(lexer)
        parser = VshParser(token_stream)

        visitor = _Visitor()
        self._output = visitor.visit(parser.program())

        return True

    @property
    def output(self) -> str:
        return self._output
