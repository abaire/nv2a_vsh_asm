"""Capturing ANTLR ErrorListener implementation."""

# ruff: noqa:  N802 Function name should be lowercase
# ruff: noqa:  N803 Argument name should be lowercase

# pylint: disable=invalid-name
# pylint: disable=missing-function-docstring
# pylint: disable=wrong-import-order
# pylint: disable=too-many-arguments

from __future__ import annotations

import typing

from antlr4.error.ErrorListener import ErrorListener


class VshError(typing.NamedTuple):
    message: str
    symbol: str
    line: int
    column: int


class VshErrorListener(ErrorListener):
    """ErrorListener implementation for the nv2a vertex shader grammar."""

    def __init__(self):
        self.errors = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        del recognizer
        del e
        self.errors.append(VshError(msg, offendingSymbol, line, column))

    @property
    def num_errors(self):
        return len(self.errors)

    @property
    def has_errors(self):
        return self.num_errors > 0

    @property
    def ok(self):
        return not self.has_errors

    def __str__(self):
        ret = self.__repr__()[:-1]
        ret += f" NE:{len(self.errors)}>"
        ret += str(self.errors)
        return ret
