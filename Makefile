UNAME_S := $(shell uname -s)
GRAMMAR_OUT := nv2avsh/grammar/vsh

ifeq ($(UNAME_S),Linux)
ANTLR = antlr4
endif
ifeq ($(UNAME_S),Darwin)
ANTLR = antlr
endif

.PHONY: all
all: $(GRAMMAR_OUT)/VshParser.py

.PHONY: install
install:
	python setup.py antlr install

$(GRAMMAR_OUT)/VshParser.py: nv2avsh/grammar/Vsh.g4
	python setup.py antlr build

.PHONY: clean
clean:
	rm -f $(GRAMMAR_OUT)/Vsh.interp \
		$(GRAMMAR_OUT)/Vsh.tokens \
		$(GRAMMAR_OUT)/VshLexer.interp \
		$(GRAMMAR_OUT)/VshLexer.py \
		$(GRAMMAR_OUT)/VshLexer.tokens \
		$(GRAMMAR_OUT)/VshListener.py \
		$(GRAMMAR_OUT)/VshParser.py \
		$(GRAMMAR_OUT)/VshVisitor.py
