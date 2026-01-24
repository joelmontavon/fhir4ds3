"""
Forked fhirpath-py parser integration for FHIR4DS

This module contains a customized version of fhirpath-py parser
integrated with FHIR4DS-specific enhancements.

Original source: https://github.com/beda-software/fhirpath-py/tree/master/fhirpathpy/parser
"""

import sys
from antlr4 import *
from antlr4.tree.Tree import ParseTreeWalker
from antlr4.error.ErrorListener import ErrorListener
from antlr4.error.Errors import LexerNoViableAltException
from .generated.FHIRPathLexer import FHIRPathLexer
from .generated.FHIRPathParser import FHIRPathParser
from .ASTPathListener import ASTPathListener


def recover(e):
    """Error recovery function - re-raises exceptions for proper error handling"""
    raise e


def parse(value):
    """
    Parse a FHIRPath expression using the forked fhirpath-py parser

    Args:
        value: FHIRPath expression string to parse

    Returns:
        Parsed AST structure compatible with fhirpath-py

    Raises:
        Various parsing exceptions for invalid syntax
    """
    textStream = InputStream(value)

    astPathListener = ASTPathListener()
    errorListener = ErrorListener()

    lexer = FHIRPathLexer(textStream)
    lexer.recover = recover
    lexer.removeErrorListeners()
    lexer.addErrorListener(errorListener)

    parser = FHIRPathParser(CommonTokenStream(lexer))
    parser.buildParseTrees = True
    parser.removeErrorListeners()
    parser.addErrorListener(errorListener)

    walker = ParseTreeWalker()
    walker.walk(astPathListener, parser.expression())

    return astPathListener.parentStack[0]


# Expose main parse function
__all__ = ['parse']