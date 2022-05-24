"""Tests for Vsh ANTLR parsing implementation."""
import pathlib
import os
import unittest

import antlr4
from build.grammar.VshLexer import VshLexer
from build.grammar.VshParser import VshParser
from build.grammar.VshListener import VshListener
from test.vsh_error_listener import VshErrorListener

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


class VSHParserTestCase(unittest.TestCase):
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
        with open(all_input) as infile:
            self._parse(infile.read())
        self.assertTrue(self._error_listener.ok)


if __name__ == "__main__":
    unittest.main()