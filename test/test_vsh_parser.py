"""Tests for Vsh ANTLR parsing implementation."""

# pylint: disable=missing-function-docstring
# pylint: disable=too-many-public-methods
# pylint: disable=wrong-import-order

import pathlib
import os
import unittest

import antlr4
from nv2avsh.grammar.vsh.VshLexer import VshLexer
from nv2avsh.grammar.vsh.VshParser import VshParser
from nv2avsh.grammar.vsh.VshListener import VshListener
from nv2avsh.nv2a_vsh_asm.vsh_error_listener import VshErrorListener

_RESOURCE_PATH = os.path.dirname(pathlib.Path(__file__).resolve())

_JUST_COMMENTS = """
/* Single line block comment */

/*
 * Multiline
 * Block
 * Comment
 */

 // Line comment
 ; Alternative line comment

     // Line comment prefixed with whitespace
"""

_COMBINED = """
MOV oD0.xyzw, v3 // A comment should not break combining
+ RCP R1.w, R1.w
"""


class VSHParserTestCase(unittest.TestCase):
    """Tests for the vertex shader ANTLR parsing implementation."""

    def __init__(self, methodName: str = ...) -> None:
        super().__init__(methodName)
        self._error_listener = None

    def _make_parser(self, input_text: str):
        lexer = VshLexer(antlr4.InputStream(input_text))
        stream = antlr4.CommonTokenStream(lexer)
        parser = VshParser(stream)

        self._error_listener = VshErrorListener()

        lexer.removeErrorListeners()
        lexer.addErrorListener(self._error_listener)
        parser.removeErrorListeners()
        parser.addErrorListener(self._error_listener)

        return parser

    def _parse(self, input_text: str):
        parser = self._make_parser(input_text)
        tree = parser.program()

        listener = VshListener()
        walker = antlr4.ParseTreeWalker()
        walker.walk(listener, tree)

    def test_empty(self):
        self._parse("")
        self.assertTrue(self._error_listener.ok)

    def test_comments(self):
        self._parse(_JUST_COMMENTS)
        self.assertTrue(self._error_listener.ok)

    def test_garbage_fails(self):
        self._parse("zxcvsd/2390m!!")
        self.assertGreater(self._error_listener.num_errors, 0)

        first_error = self._error_listener.errors[0]
        self.assertEqual(first_error.line, 1)

    def test_garbage_inside_fails(self):
        self._parse("\n//Commented garbage\nzxcvsd/2390m!!")
        self.assertGreater(self._error_listener.num_errors, 0)

        first_error = self._error_listener.errors[0]
        self.assertEqual(first_error.line, 3)

    def test_add(self):
        self._parse("add r0, v0, v1\n")
        self.assertTrue(self._error_listener.ok)

    def test_all(self):
        all_input = os.path.join(_RESOURCE_PATH, "all.vsh")
        with open(all_input, encoding="utf-8") as infile:
            self._parse(infile.read())
        self.assertTrue(self._error_listener.ok)

    def test_combined(self):
        self._parse(_JUST_COMMENTS)
        self.assertTrue(self._error_listener.ok)

    def test_cx_bracketed(self):
        self._parse("add r0, v0, c[12]")
        self.assertTrue(self._error_listener.ok)

    def test_cx_relative_a_first(self):
        self._parse("add r0, v0, c[A0+12]")
        self.assertTrue(self._error_listener.ok)

    def test_cx_relative_a_second(self):
        self._parse("add r0, v0, c[12 + A0]")
        self.assertTrue(self._error_listener.ok)

    def test_negated_input(self):
        self._parse("add r0, -v0, c1")
        self.assertTrue(self._error_listener.ok)

    def test_uniform_matrix4(self):
        self._parse("#test matrix4 13")
        self.assertTrue(self._error_listener.ok)

    def test_uniform_vector(self):
        self._parse("#test vector 12")
        self.assertTrue(self._error_listener.ok)

    def test_uniform_output(self):
        self._parse("mov #test, r1")
        self.assertTrue(self._error_listener.ok)

    def test_r12(self):
        self._parse("mov r11, r12")
        self.assertTrue(self._error_listener.ok)


if __name__ == "__main__":
    unittest.main()
