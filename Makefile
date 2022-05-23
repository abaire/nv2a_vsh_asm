UNAME_S := $(shell uname -s)
GRAMMAR_OUT := build

ifeq ($(UNAME_S),Linux)
ANTLR = antlr4
endif
ifeq ($(UNAME_S),Darwin)
ANTLR = antlr
endif

.PHONY: all
all: $(GRAMMAR_OUT)/VshParser.py

$(GRAMMAR_OUT)/VshParser.py: grammar/Vsh.g4
	$(ANTLR) -Dlanguage=Python3 $< -o $(GRAMMAR_OUT) -visitor

.PHONY: clean
clean:
	rm -f $(GRAMMAR_OUT)/grammar/Vsh.interp \
		$(GRAMMAR_OUT)/grammar/Vsh.tokens \
		$(GRAMMAR_OUT)/grammar/VshLexer.interp \
		$(GRAMMAR_OUT)/grammar/VshLexer.py \
		$(GRAMMAR_OUT)/grammar/VshLexer.tokens \
		$(GRAMMAR_OUT)/grammar/VshListener.py \
		$(GRAMMAR_OUT)/grammar/VshParser.py \
		$(GRAMMAR_OUT)/grammar/VshVisitor.py
