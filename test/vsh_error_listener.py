import collections
from antlr4.error.ErrorListener import ErrorListener

VshError = collections.namedtuple("VshError", ["message", "symbol", "line", "column"])


class VshErrorListener(ErrorListener):
    """ErrorListener implementation for the nv2a vertex shader grammar."""

    def __init__(self):
        self.errors = []

    def syntaxError(self, recognizer, symbol, line, column, message, e):
        self.errors.append(VshError(message, symbol, line, column))

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
