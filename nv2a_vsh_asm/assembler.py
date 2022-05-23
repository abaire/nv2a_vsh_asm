"""nv2a vertex shader language assembler"""
import antlr4
from build.grammar.VshLexer import VshLexer
from build.grammar.VshParser import VshParser
from build.grammar.VshVisitor import VshVisitor

from . import vsh_encoder

class _Visitor(VshVisitor):
    def visitOp_add(self, ctx: VshParser.Op_addContext):
        return super().visitOp_add(ctx)


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
        print(f"OUTPUT: {self._output}")

        dst = vsh_encoder.DestinationRegister(vsh_encoder.gl_register_file.PROGRAM_OUTPUT)
        ins = vsh_encoder.Instruction(vsh_encoder.prog_opcode.OPCODE_MOV, dst)
        vsh_encoder.encode([ins])

        return True

    @property
    def output(self) -> str:
        return self._output
